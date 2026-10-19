"""Read the local .env explicitly; never inherit a remote database by accident."""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import dotenv_values


_values = dotenv_values(Path(__file__).resolve().parent.parent / '.env', interpolate=False)
for _key in ('DJANGO_SECRET_KEY', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD'):
    if not _values.get(_key):
        raise ImproperlyConfigured(f'Local .env must define {_key}; values are not printed.')
for _key in ('DJANGO_SECRET_KEY', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD'):
    os.environ[_key] = _values[_key]
os.environ['POSTGRES_HOST'] = _values.get('POSTGRES_HOST') or '127.0.0.1'
os.environ['POSTGRES_PORT'] = _values.get('POSTGRES_PORT') or '5432'
if os.environ['POSTGRES_HOST'] not in {'localhost', '127.0.0.1', '::1'}:
    raise ImproperlyConfigured('Local transfer settings require a loopback PostgreSQL host.')
os.environ['POSTGRES_TEST_DB'] = 'local_transfer_tests_not_authorized'
os.environ['PYTHON_DOTENV_DISABLED'] = '1'
os.environ['DJANGO_ENVIRONMENT'] = 'development'
os.environ['DJANGO_DEBUG'] = 'False'
os.environ['DJANGO_ALLOWED_HOSTS'] = 'localhost,127.0.0.1'
os.environ['DJANGO_CORS_ALLOWED_ORIGINS'] = ''
os.environ['DJANGO_CSRF_TRUSTED_ORIGINS'] = ''

from .settings import *  # noqa: E402,F403
