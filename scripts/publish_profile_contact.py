"""Update only the approved public biography, with backup and compare-and-swap."""
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
from portfolio.models import Perfil

INTRO = ('Soy desarrollador de software de Córdoba, Argentina, y actualmente curso la '
         'Tecnicatura Superior en Desarrollo de Software en el Instituto Superior '
         'Politécnico de Córdoba (ISPC).')
CONTACT = 'Teléfono: 3517587047\n\nCorreo: nahuel.cba.48@gmail.com'
PREVIOUS_BODY = (
    'Me interesa construir aplicaciones web, resolver problemas técnicos, integrar APIs y profundizar en la calidad del software y las pruebas automatizadas. Mi recorrido incluye tecnologías frontend y backend, desarrollo con WordPress y soporte técnico informático.\n\n'
    'Hoy estoy enfocado en seguir creciendo como desarrollador y contribuir a proyectos reales.'
)
PREVIOUS_APPROVED_BODY = (
    'Me interesa construir aplicaciones web, resolver problemas técnicos y conectar servicios mediante APIs e inteligencia artificial. '
    'Desarrollo chatbots inteligentes, integro WhatsApp con la API de Meta, implemento formularios de contacto con envío de correos y exploro soluciones IoT con ESP32. '
    'Mi recorrido incluye tecnologías frontend y backend, desarrollo con WordPress y soporte técnico informático.\n\n'
    'Hoy estoy enfocado en seguir creciendo como desarrollador, profundizar en la calidad del software y las pruebas automatizadas, y contribuir a proyectos reales.'
)
BODY = (
    'Me gusta crear aplicaciones web y encontrar soluciones a problemas técnicos. '
    'En mis proyectos combino frontend y backend, integro APIs e inteligencia artificial, desarrollo chatbots para WhatsApp con la API de Meta y conecto formularios con servicios de correo. '
    'También exploro soluciones IoT con ESP32 y cuento con experiencia en WordPress y soporte técnico informático.\n\n'
    'Hoy busco seguir creciendo como desarrollador, mejorar la calidad de lo que construyo con pruebas automatizadas y aportar a proyectos reales.'
)

with connection.cursor() as cursor:
    cursor.execute('SELECT * FROM public.portfolio_perfil WHERE singleton_key=1')
    columns = [column.name for column in cursor.description]
    rows = cursor.fetchall()
if len(rows) != 1:
    raise RuntimeError('Expected exactly one public profile.')
before = dict(zip(columns, rows[0]))
if not before['is_published']:
    raise RuntimeError('The profile is not published.')
biography = before['biography']
if biography == BODY + '\n\n' + CONTACT:
    updated = biography
elif biography in (INTRO + '\n\n' + PREVIOUS_BODY, PREVIOUS_BODY + '\n\n' + CONTACT,
                   PREVIOUS_APPROVED_BODY + '\n\n' + CONTACT):
    updated = BODY + '\n\n' + CONTACT
else:
    raise RuntimeError('Unexpected biography; review before changing it.')

backup = ROOT / 'backups' / ('profile-contact-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '.json')
backup.parent.mkdir(exist_ok=True)
backup.write_text(json.dumps(before, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
with transaction.atomic():
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL lock_timeout='5s'")
        cursor.execute("SET LOCAL statement_timeout='10s'")
        if updated != biography:
            cursor.execute('UPDATE public.portfolio_perfil SET biography=%s, updated_at=NOW() '
                           'WHERE id=%s AND biography=%s RETURNING id', [updated, before['id'], biography])
            if cursor.fetchone() is None:
                raise RuntimeError('Profile changed concurrently; rolled back.')
        cursor.execute('SELECT * FROM public.portfolio_perfil WHERE id=%s', [before['id']])
        after = dict(zip(columns, cursor.fetchone()))
        if any(after[key] != value for key, value in before.items() if key not in ('biography', 'updated_at')):
            raise RuntimeError('Unrelated profile field changed; rolled back.')
        cursor.execute('SET LOCAL search_path TO public, pg_catalog')
    public = Perfil.objects.get(pk=before['id']).to_public_dict()
    assert public['biography'] == updated
    if not args.apply:
        transaction.set_rollback(True)

print(json.dumps({'applied': args.apply, 'schema': 'public', 'profileId': before['id'],
                  'biographyUpdated': updated != biography, 'apiSerializationVerified': True,
                  'backup': str(backup.relative_to(ROOT))}))
