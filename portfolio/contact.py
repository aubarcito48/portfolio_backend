"""Bounded public contact form. Send only to the portfolio owner through HTTPS."""
from collections import deque
import json
import logging
import re
import threading
import time
import unicodedata
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from django import forms
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt

from .aubar_views import unique_object

logger = logging.getLogger(__name__)
_attempts = deque()
_lock = threading.Lock()
_sending = threading.BoundedSemaphore(2)


class ContactForm(forms.Form):
    nombre = forms.CharField(min_length=2, max_length=100)
    telefono = forms.CharField(min_length=7, max_length=32)
    email = forms.EmailField(max_length=254)
    asunto = forms.CharField(min_length=3, max_length=160)
    mensaje = forms.CharField(min_length=10, max_length=3000)
    website = forms.CharField(required=False, max_length=200)  # Honeypot.
    solicitud = forms.UUIDField()

    def clean(self):
        data = super().clean()
        for key in ('nombre', 'telefono', 'email', 'asunto', 'mensaje', 'website'):
            value = data.get(key, '')
            if any(unicodedata.category(char) in {'Cc', 'Cf', 'Cs'}
                   and not (key == 'mensaje' and char in '\n\r\t') for char in value):
                self.add_error(key, 'invalid')
        phone = data.get('telefono', '')
        if phone and (not re.fullmatch(r'\+?[0-9 ()\-.]+', phone)
                      or not 7 <= len(re.sub(r'\D', '', phone)) <= 15):
            self.add_error('telefono', 'invalid')
        return data


class DeliveryUnavailable(Exception):
    pass


def deliver(data):
    """Plain text with a fixed recipient/from; visitor email goes in Reply-To only."""
    payload = {
        'from': settings.CONTACT_FROM_EMAIL,
        'to': ['nahuel.cba.48@gmail.com'],
        'reply_to': data['email'],
        'subject': '[Portfolio] ' + data['asunto'],
        'text': ('Nuevo contacto desde el portfolio\n\n'
                 f"Nombre y apellido: {data['nombre']}\n"
                 f"Teléfono: {data['telefono']}\n"
                 f"Correo: {data['email']}\n"
                 f"Asunto: {data['asunto']}\n\n{data['mensaje']}"),
    }
    request = Request('https://api.resend.com/emails', method='POST',
        data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        headers={'Authorization': 'Bearer ' + settings.RESEND_API_KEY,
                 'Content-Type': 'application/json', 'User-Agent': 'Portfolio-Contact/1.0',
                 'Idempotency-Key': 'portfolio-contact/' + str(data['solicitud'])})
    try:
        with urlopen(request, timeout=12) as result:
            raw = result.read(16385)
            if result.status not in (200, 201) or len(raw) > 16384:
                raise DeliveryUnavailable()
        body = json.loads(raw)
        if not isinstance(body, dict) or not isinstance(body.get('id'), str) or not body['id']:
            raise DeliveryUnavailable()
    except HTTPError as error:
        logger.error('delivery_failed', extra={'status_code': error.code})
        error.close()
        raise DeliveryUnavailable() from None
    except Exception:
        # Never log form values, headers, provider bodies or exception text.
        logger.error('delivery_failed')
        raise DeliveryUnavailable() from None


def response(code, status=200, **extra):
    result = JsonResponse({'codigo': code, **extra}, status=status)
    result['X-Content-Type-Options'] = 'nosniff'
    return result


@csrf_exempt  # Public form, no sessions/cookies; only a fixed recipient is allowed.
@never_cache
def contact(request):
    if request.method == 'OPTIONS':
        result = response('OK')
        result['Allow'] = 'POST, OPTIONS'
        return result
    if request.method != 'POST':
        result = response('METODO_NO_PERMITIDO', 405)
        result['Allow'] = 'POST, OPTIONS'
        return result
    origin = request.headers.get('Origin')
    allowed = settings.CORS_ALLOWED_ORIGINS + [f'{request.scheme}://{request.get_host()}']
    if origin is not None and origin not in allowed:
        return response('ORIGEN_NO_PERMITIDO', 403)
    if request.content_type != 'application/json':
        return response('ENTRADA_INVALIDA', 415)
    raw = request.read(16385)
    if len(raw) > 16384:
        return response('ENTRADA_INVALIDA', 413)
    try:
        data = json.loads(raw, object_pairs_hook=unique_object)
        if (not isinstance(data, dict) or set(data) - set(ContactForm.base_fields)
                or any(not isinstance(value, str) for value in data.values())):
            raise ValueError()
    except (ValueError, TypeError, UnicodeDecodeError, RecursionError):
        return response('ENTRADA_INVALIDA', 400)
    form = ContactForm(data)
    if not form.is_valid():
        return response('ENTRADA_INVALIDA', 400, campos=list(form.errors))
    if form.cleaned_data['website']:
        return response('MENSAJE_ENVIADO')  # Silently discard obvious automated submissions.
    if not settings.RESEND_API_KEY or not settings.CONTACT_FROM_EMAIL:
        return response('CONTACTO_NO_DISPONIBLE', 503)
    # A small demo budget shared across all visitors in this process. Bound memory
    # and provider spend; this is not a distributed quota or CAPTCHA replacement.
    now = time.monotonic()
    with _lock:
        while _attempts and _attempts[0] <= now - 86400:
            _attempts.popleft()
        recent = sum(stamp > now - 3600 for stamp in _attempts)
        if recent >= 10 or len(_attempts) >= 30:
            result = response('LIMITE_ALCANZADO', 429)
            result['Retry-After'] = str(max(1, int(
                (_attempts[-10] + 3600 if recent >= 10 else _attempts[0] + 86400) - now) + 1))
            return result
        _attempts.append(now)
    if not _sending.acquire(blocking=False):
        return response('CONTACTO_OCUPADO', 429)
    try:
        deliver(form.cleaned_data)
        return response('MENSAJE_ENVIADO')
    except DeliveryUnavailable:
        return response('CONTACTO_NO_DISPONIBLE', 503)
    finally:
        _sending.release()
