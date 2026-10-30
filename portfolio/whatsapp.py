"""Small, single-process portfolio demo using Meta's signed Cloud API webhooks.

Sessions, deduplication and the bounded background queue are intentionally ephemeral.
Deploy with one Gunicorn worker; see docs/WHATSAPP.md before enabling.
"""
from collections import OrderedDict, deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
import hashlib
import hmac
import json
import logging
import re
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import close_old_connections
from django.http import HttpResponse, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt

from .aubar_service import AubarUnavailable, answer
from .aubar_views import valid_text
from config.safe_logging import safe_error_type


TRIGGERS = {
    'Hola Nahuel, vi tu portfolio y me gustaría contactarte.': 'es',
    'Hi Nahuel, I saw your portfolio and would like to get in touch.': 'en',
}
WELCOME = {
    'es': ('¡Hola! Soy Aubar, el asistente automático del portfolio de Nahuel. '
           'Podés preguntarme por sus proyectos, tecnologías y formación. '
           'Tus preguntas se procesan con IA (Groq); no compartas datos sensibles. '
           'Escribí SALIR para apagar el bot o HUMANO para dejar de recibir respuestas automáticas. '
           'Esto no avisa ni garantiza una respuesta de Nahuel.'),
    'en': ("Hi! I'm Aubar, the automated assistant for Nahuel's portfolio. "
           'Ask me about his projects, skills and education. '
           'Your questions are processed with AI (Groq); do not share sensitive data. '
           'Send STOP to turn off the bot or HUMAN to stop automated replies. '
           'This does not notify Nahuel or guarantee a personal reply.'),
}
STOP = {'salir', 'stop', 'humano', 'human'}
SESSION_SECONDS = 1800
_sessions = OrderedDict()
_seen = OrderedDict()
_rate = deque()
_lock = threading.Lock()
_slots = threading.BoundedSemaphore(20)
_executor = None  # Created after Gunicorn forks, on the first accepted webhook.
logger = logging.getLogger(__name__)


@dataclass
class Session:
    language: str
    expires: float
    history: list = field(default_factory=list)
    requests: deque = field(default_factory=deque)


class WhatsAppSendError(Exception):
    def __init__(self, status, code=None, subcode=None):
        self.status = status
        self.code = code
        self.subcode = subcode
        super().__init__('WhatsApp delivery rejected')


def send_text(recipient, text):
    """Fixed Graph host; credentials and provider error bodies never reach logs."""
    # Opt-in workaround for Meta test allowlists in Argentina. Rewrite only the
    # exact configured recipient's 549 variant; never normalize unrelated numbers.
    test_recipient = settings.WHATSAPP_TEST_RECIPIENT
    if (re.fullmatch(r'54[0-9]{10}', test_recipient)
            and recipient == '549' + test_recipient[2:]):
        recipient = test_recipient
    request = Request(
        f'https://graph.facebook.com/{settings.WHATSAPP_GRAPH_VERSION}/'
        f'{settings.WHATSAPP_PHONE_NUMBER_ID}/messages',
        data=json.dumps({'messaging_product': 'whatsapp', 'to': recipient,
                         'type': 'text', 'text': {'body': text, 'preview_url': False}}).encode(),
        headers={'Authorization': 'Bearer ' + settings.WHATSAPP_ACCESS_TOKEN,
                 'Content-Type': 'application/json'}, method='POST')
    try:
        with urlopen(request, timeout=10) as response:
            if response.status != 200:
                raise WhatsAppSendError(response.status)
    except HTTPError as error:
        # Only numeric diagnostics survive. Never retain the provider message/body.
        code = subcode = None
        try:
            with error:
                raw = error.read(16385)
            if len(raw) <= 16384:
                details = json.loads(raw).get('error', {})
                code = details.get('code')
                subcode = details.get('error_subcode')
        except (ValueError, TypeError, AttributeError, OSError):
            pass
        raise WhatsAppSendError(error.code, code, subcode) from None


def _prune(now):
    for phone in list(_sessions):
        if _sessions[phone].expires <= now:
            del _sessions[phone]
    while _seen and next(iter(_seen.values())) <= now - 86400:
        _seen.popitem(last=False)
    while _rate and _rate[0] <= now - 60:
        _rate.popleft()


def process_message(message):
    """Called serially by the background executor, never in the webhook response path."""
    phone, text = message['from'], message['text']['body']
    now = time.time()
    with _lock:
        _prune(now)
        session = _sessions.get(phone)
        language = TRIGGERS.get(text)  # Exact, whole-message match, including punctuation.
        if session is None and language is None:
            return
        if session and text.strip().casefold() in STOP:
            del _sessions[phone]
            reply = ('Bot desactivado. No recibirás más respuestas automáticas.'
                     if session.language == 'es' else 'Bot disabled. Automated replies are now off.')
        else:
            # A repeated activation phrase cannot bypass a conversation's rate limit.
            if session is None:
                if len(_sessions) >= 1000:
                    return
                session = Session(language, now + SESSION_SECONDS)
                _sessions[phone] = session
            while session.requests and session.requests[0] <= now - 60:
                session.requests.popleft()
            if len(session.requests) >= 5 or len(_rate) >= 10:
                return
            session.requests.append(now)
            _rate.append(now)
            session.expires = now + SESSION_SECONDS
            if language:
                session.language = language
                session.history.clear()
                reply = WELCOME[language]
            else:
                reply = None
    if reply is None:
        try:
            reply = answer(text, list(session.history), session.language)
        except AubarUnavailable:
            reply = ('Ahora no puedo responder. Podés volver a intentar en un momento.'
                     if session.language == 'es' else "I can't respond right now. Please try again shortly.")
        else:
            # Match the existing chat's 8-message / 6,000-character history budget.
            session.history.extend([{'role': 'user', 'content': text},
                                    {'role': 'assistant', 'content': reply[:2000]}])
            while (len(session.history) > 8
                   or sum(len(item['content']) for item in session.history) > 6000):
                del session.history[:2]
    send_text(phone, reply)


def _run_batch(messages):
    try:
        close_old_connections()
        for message in messages:
            # A slow queue must not answer old messages after the service window.
            if abs(time.time() - int(message['timestamp'])) > 300:
                continue
            try:
                process_message(message)
            except WhatsAppSendError as error:
                logger.error('whatsapp_delivery_failed', extra={
                    'status_code': error.status, 'meta_code': error.code,
                    'meta_subcode': error.subcode})
            except Exception as error:
                # Do not log message contents, phone numbers, tokens or exceptions.
                logger.error('whatsapp_processing_failed', extra={
                    'failure_type': safe_error_type(error)})
    finally:
        close_old_connections()
        _slots.release()


def enqueue(messages):
    global _executor
    if not _slots.acquire(blocking=False):
        return False
    with _lock:
        now = time.time()
        _prune(now)
        fresh = []
        for message in messages:
            if message['id'] not in _seen:
                _seen[message['id']] = now
                fresh.append(message)
        if not fresh:
            _slots.release()
            return True
        # Never evict live deduplication records just to admit more traffic.
        if len(_seen) > 10000:
            for message in fresh:
                del _seen[message['id']]
            _slots.release()
            return False
        try:
            if _executor is None:
                _executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='whatsapp')
            _executor.submit(_run_batch, fresh)
        except Exception:
            for message in fresh:
                _seen.pop(message['id'], None)
            _slots.release()
            return False
    return True


def extract_messages(data):
    """Ignore statuses, other numbers, unsupported media, stale events and bad shapes."""
    messages = []
    if not isinstance(data, dict) or data.get('object') != 'whatsapp_business_account':
        return messages
    entries = data.get('entry', [])
    if not isinstance(entries, list):
        raise ValueError()
    for entry in entries:
        for change in entry.get('changes', []):
            if change.get('field') != 'messages':
                continue
            value = change.get('value', {})
            if value.get('metadata', {}).get('phone_number_id') != settings.WHATSAPP_PHONE_NUMBER_ID:
                continue
            for message in value.get('messages', []):
                if not isinstance(message, dict) or message.get('type') != 'text':
                    continue
                phone, identifier = message.get('from'), message.get('id')
                body = message.get('text', {}).get('body')
                if (not isinstance(phone, str) or not re.fullmatch(r'[0-9]{6,20}', phone)
                        or not isinstance(identifier, str) or not 1 <= len(identifier) <= 256
                        or not valid_text(body, 1200)):
                    continue
                try:
                    if abs(time.time() - int(message.get('timestamp', ''))) > 300:
                        continue
                except (ValueError, TypeError, OverflowError):
                    continue
                messages.append(message)
                if len(messages) > 100:
                    raise ValueError()
    return messages


@csrf_exempt  # Meta authenticates POST bodies with HMAC, not browser cookies.
@never_cache
def webhook(request):
    if not settings.WHATSAPP_ENABLED:
        return HttpResponse(status=404)
    if request.method == 'GET':
        token = request.GET.get('hub.verify_token', '')
        if (settings.WHATSAPP_VERIFY_TOKEN and request.GET.get('hub.mode') == 'subscribe'
                and hmac.compare_digest(token.encode(), settings.WHATSAPP_VERIFY_TOKEN.encode())):
            return HttpResponse(request.GET.get('hub.challenge', ''), content_type='text/plain')
        return HttpResponse(status=403)
    if request.method != 'POST':
        result = HttpResponse(status=405)
        result['Allow'] = 'GET, POST'
        return result
    if request.content_type != 'application/json':
        return HttpResponse(status=415)
    body = request.read(262145)
    if len(body) > 262144:
        return HttpResponse(status=413)
    signature = request.headers.get('X-Hub-Signature-256', '')
    expected = 'sha256=' + hmac.new(settings.WHATSAPP_APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
    if not settings.WHATSAPP_APP_SECRET or not hmac.compare_digest(signature.encode(), expected.encode()):
        return HttpResponse(status=403)
    try:
        messages = extract_messages(json.loads(body))
    except (ValueError, TypeError, AttributeError, UnicodeDecodeError, RecursionError):
        return HttpResponse(status=400)
    if messages and not enqueue(messages):
        return HttpResponse(status=503)  # Ask Meta to retry; nothing has been admitted.
    return JsonResponse({'status': 'ok'})
