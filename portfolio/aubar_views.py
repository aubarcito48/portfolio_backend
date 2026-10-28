"""Public, stateless chat endpoint with bounded input, rate and concurrency."""
from collections import deque
import json
import threading
import time
import unicodedata

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt

from .aubar_service import AubarQuota, AubarUnavailable, answer

_requests = deque()
_rate_lock = threading.Lock()
_generation = threading.Lock()


def response(payload, status=200):
    result = JsonResponse(payload, status=status)
    result['X-Content-Type-Options'] = 'nosniff'
    if status == 429:
        result['Retry-After'] = '60'
    return result


def valid_text(value, limit):
    return (isinstance(value, str) and 1 <= len(value.strip()) <= limit and len(value) <= limit
            and not any(unicodedata.category(c) in {'Cc', 'Cf', 'Cs'} and c not in '\n\r\t' for c in value))


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate key')
        result[key] = value
    return result


@csrf_exempt  # No cookies, authentication, mutations or private data in this public endpoint.
@never_cache
def chat(request):
    if request.method == 'OPTIONS':
        result = response({}, 200)
        result['Allow'] = 'POST, OPTIONS'
        return result
    if request.method != 'POST':
        result = response({'codigo': 'METODO_NO_PERMITIDO'}, 405)
        result['Allow'] = 'POST, OPTIONS'
        return result
    origin = request.headers.get('Origin')
    allowed_origins = settings.CORS_ALLOWED_ORIGINS + [f'{request.scheme}://{request.get_host()}']
    if origin is not None and origin not in allowed_origins:
        return response({'codigo': 'ORIGEN_NO_PERMITIDO'}, 403)
    if request.content_type != 'application/json':
        return response({'codigo': 'ENTRADA_INVALIDA'}, 415)
    body = request.read(16385)
    if len(body) > 16384:
        return response({'codigo': 'ENTRADA_INVALIDA'}, 413)
    try:
        data = json.loads(body, object_pairs_hook=unique_object)
        if not isinstance(data, dict) or set(data) - {'mensaje', 'historial', 'idioma'}:
            raise ValueError()
        message, history, language = data.get('mensaje'), data.get('historial', []), data.get('idioma', 'es')
        if not valid_text(message, 1200) or language not in ('es', 'en'):
            raise ValueError()
        if not isinstance(history, list) or len(history) > 8:
            raise ValueError()
        for item in history:
            if (not isinstance(item, dict) or set(item) != {'role', 'content'}
                    or item['role'] not in ('user', 'assistant') or not valid_text(item['content'], 2000)):
                raise ValueError()
        if sum(len(item['content']) for item in history) > 6000:
            raise ValueError()
    except (ValueError, UnicodeDecodeError, RecursionError, TypeError):
        return response({'codigo': 'ENTRADA_INVALIDA'}, 400)
    with _rate_lock:
        now = time.monotonic()
        while _requests and _requests[0] <= now - 60:
            _requests.popleft()
        if len(_requests) >= 10:
            return response({'codigo': 'LIMITE_ALCANZADO'}, 429)
        _requests.append(now)
    if not _generation.acquire(blocking=False):
        return response({'codigo': 'AUBAR_OCUPADO'}, 429)
    try:
        return response({'respuesta': answer(message.strip(), history, language)})
    except AubarQuota:
        return response({'codigo': 'LIMITE_ALCANZADO'}, 429)
    except AubarUnavailable:
        return response({'codigo': 'AUBAR_NO_DISPONIBLE'}, 503)
    finally:
        _generation.release()
