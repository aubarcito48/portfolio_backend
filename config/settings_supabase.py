"""Explicit opt-in settings for a NEW, private Django schema in Supabase."""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.db.backends.signals import connection_created
from dotenv import dotenv_values


_path = Path(__file__).resolve().parent.parent / '.env.supabase'
if not _path.is_file():
    raise ImproperlyConfigured('Create .env.supabase from config/supabase.env.example.')
_values = dotenv_values(_path, interpolate=False)
for _key in ('DJANGO_SECRET_KEY', 'DJANGO_ALLOWED_HOSTS', 'POSTGRES_DB',
             'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_HOST', 'POSTGRES_PORT'):
    if not _values.get(_key) or _values[_key].startswith('replace-with-'):
        raise ImproperlyConfigured(f'Complete {_key} in .env.supabase; values are not printed.')

# No fallback to .env or inherited local database credentials.
for _key in ('DJANGO_SECRET_KEY', 'DJANGO_ALLOWED_HOSTS', 'POSTGRES_DB',
             'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_HOST', 'POSTGRES_PORT',
             'DJANGO_CORS_ALLOWED_ORIGINS', 'DJANGO_CSRF_TRUSTED_ORIGINS'):
    os.environ[_key] = _values.get(_key) or ''
os.environ['PYTHON_DOTENV_DISABLED'] = '1'
os.environ['DJANGO_ENVIRONMENT'] = 'production'
os.environ['DJANGO_DEBUG'] = 'False'
os.environ['POSTGRES_TEST_DB'] = 'supabase_tests_not_authorized'

from .settings import *  # noqa: E402,F403

SUPABASE_MIGRATION_SCHEMA = 'portfolio_django'
_sslmode = _values.get('POSTGRES_SSLMODE') or 'require'
if _sslmode not in {'require', 'verify-full'}:
    raise ImproperlyConfigured('Supabase requires sslmode=require or verify-full.')
DATABASES['default']['OPTIONS']['sslmode'] = _sslmode
if _sslmode == 'verify-full':
    _certificate = _values.get('POSTGRES_SSLROOTCERT')
    if not _certificate or not Path(_certificate).is_file():
        raise ImproperlyConfigured('verify-full requires a local POSTGRES_SSLROOTCERT file.')
    DATABASES['default']['OPTIONS']['sslrootcert'] = _certificate
DATABASES['default']['DISABLE_SERVER_SIDE_CURSORS'] = True


def _select_private_schema(sender, connection, **kwargs):
    from psycopg import sql
    with connection.cursor() as cursor:
        cursor.execute(sql.SQL('SET search_path TO {}, pg_catalog').format(
            sql.Identifier(SUPABASE_MIGRATION_SCHEMA)))


connection_created.connect(_select_private_schema, weak=False,
                          dispatch_uid='supabase_private_portfolio_schema')
