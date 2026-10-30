"""Publish the approved shorter Aubar description without touching other project data."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--apply', action='store_true')
args = parser.parse_args()
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings_supabase'
import django
django.setup()
from django.db import connection, transaction
from portfolio.management.commands.load_aubar_bot import PROJECT

previous = (
    'Asistente de escritorio con un avatar animado en una pantalla Waveshare ESP32-S3. '
    'Combina firmware en C++ y un panel de control en Python para manejar 28 expresiones '
    'y 23 animaciones por voz. Integra conversaciones con Groq, respuestas habladas con '
    'Dora y comandos para buscar y reproducir videos de YouTube desde la PC.'
)
with connection.cursor() as cursor:
    cursor.execute('SELECT * FROM public.portfolio_proyecto WHERE slug=%s', ['aubar-bot'])
    columns = [column.name for column in cursor.description]
    rows = cursor.fetchall()
if len(rows) != 1:
    raise RuntimeError('Expected exactly one Aubar project.')
before = dict(zip(columns, rows[0]))
if not before['is_published'] or before['description'] not in (previous, PROJECT['description']):
    raise RuntimeError('Unexpected published description; review before changing it.')
backup = ROOT / 'backups' / ('aubar-description-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '.json')
backup.parent.mkdir(exist_ok=True)
backup.write_text(json.dumps(before, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
with transaction.atomic():
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL lock_timeout='5s'")
        cursor.execute("SET LOCAL statement_timeout='10s'")
        cursor.execute('UPDATE public.portfolio_proyecto SET description=%s '
                       'WHERE id=%s AND description=%s RETURNING *',
                       [PROJECT['description'], before['id'], before['description']])
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError('Project changed concurrently; rolled back.')
        after = dict(zip(columns, row))
        assert all(after[key] == value for key, value in before.items() if key != 'description')
        if not args.apply:
            transaction.set_rollback(True)
print(json.dumps({'applied': args.apply, 'schema': 'public', 'slug': 'aubar-bot',
                  'onlyDescriptionChanged': True, 'backup': str(backup.relative_to(ROOT))}))
