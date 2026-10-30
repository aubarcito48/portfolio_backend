"""Run WhatsApp + existing Aubar tests without .env or external API/database access."""
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.update(PYTHON_DOTENV_DISABLED='1', DJANGO_SETTINGS_MODULE='config.settings',
    DJANGO_ENVIRONMENT='test', DJANGO_DEBUG='False',
    DJANGO_SECRET_KEY='synthetic-whatsapp-tests-only', DJANGO_ALLOWED_HOSTS='testserver,localhost',
    POSTGRES_DB='synthetic_whatsapp', POSTGRES_USER='synthetic', POSTGRES_PASSWORD='synthetic',
    POSTGRES_TEST_DB='synthetic_whatsapp_test', GROQ_API_KEY='', WHATSAPP_ENABLED='False')
from django.conf import settings
settings.DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
import django
django.setup()
from django.test.runner import DiscoverRunner

raise SystemExit(bool(DiscoverRunner(verbosity=1, interactive=False).run_tests(
    ['portfolio.test_whatsapp', 'portfolio.test_aubar'])))
