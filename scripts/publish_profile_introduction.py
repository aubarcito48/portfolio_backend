"""Apply only the additive public profile introduction migration in Supabase."""
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
from django.db.migrations.executor import MigrationExecutor
from portfolio.models import Perfil
from portfolio.localization import localize_payload

target = ('portfolio', '0012_perfil_introduction')
with connection.cursor() as cursor:
    cursor.execute('SELECT * FROM public.portfolio_perfil ORDER BY id')
    columns = [col.name for col in cursor.description]
    before = [dict(zip(columns, row)) for row in cursor.fetchall()]
backup = ROOT / 'backups' / ('profile-introduction-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '.json')
backup.parent.mkdir(exist_ok=True)
backup.write_text(json.dumps(before, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
with transaction.atomic():
    with connection.cursor() as cursor:
        cursor.execute('SET LOCAL search_path TO public, pg_catalog')
        cursor.execute("SET LOCAL lock_timeout='5s'")
        cursor.execute("SET LOCAL statement_timeout='15s'")
    executor = MigrationExecutor(connection)
    plan = executor.migration_plan([target])
    if any((migration.app_label, migration.name) != target or backwards for migration, backwards in plan):
        raise RuntimeError('Unexpected migration plan; no changes committed.')
    executor.migrate([target])
    after = list(Perfil.objects.order_by('id').values())
    if len(after) != len(before):
        raise RuntimeError('Profile count changed; rolled back.')
    for old, new in zip(before, after):
        if any(new[key] != value for key, value in old.items()):
            raise RuntimeError('Existing profile content changed; rolled back.')
    profile = Perfil.objects.get(singleton_key=1)
    public = profile.to_public_dict()
    assert public['introduction'].startswith('Soy desarrollador de software de Córdoba')
    assert localize_payload(public, 'en')['introduction'].startswith('I am a software developer')
    if not args.apply:
        transaction.set_rollback(True)
print(json.dumps({'applied': args.apply, 'schema': 'public', 'migration': target[1],
                  'biographyUnchanged': True, 'introductionRestored': True,
                  'backup': str(backup.relative_to(ROOT))}))
