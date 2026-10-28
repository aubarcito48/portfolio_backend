"""Publish only Aubar Bot, with an ignored backup and invariants on existing rows."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--target', choices=('local', 'supabase'), required=True)
parser.add_argument('--apply', action='store_true', help='Commit the new project; otherwise roll back.')
args = parser.parse_args()
os.environ['DJANGO_SETTINGS_MODULE'] = ('config.settings_local_transfer' if args.target == 'local'
                                        else 'config.settings_supabase')

import django
django.setup()
from django.core.management import call_command
from django.db import connection, transaction
from psycopg import sql


def snapshot(schema):
    result = {}
    with connection.cursor() as cursor:
        cursor.execute('SELECT tablename FROM pg_tables WHERE schemaname=%s AND '
                       "tablename LIKE 'portfolio_%%' ORDER BY tablename", [schema])
        tables = [row[0] for row in cursor.fetchall()]
        for table in tables:
            cursor.execute(sql.SQL('SELECT * FROM {}.{} ORDER BY id').format(
                sql.Identifier(schema), sql.Identifier(table)))
            columns = [column.name for column in cursor.description]
            result[table] = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return result


def digest(value):
    return hashlib.sha256(json.dumps(value, default=str, sort_keys=True).encode()).hexdigest()


before = snapshot('public')
private_before = snapshot('portfolio_django') if args.target == 'supabase' else None
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
backup = ROOT / 'backups' / f'aubar-bot-{stamp}-{args.target}.json'
backup.parent.mkdir(exist_ok=True)
backup.write_text(json.dumps({'public': before, 'portfolio_django': private_before},
                            default=str, ensure_ascii=False, indent=2), encoding='utf-8')

with transaction.atomic():
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL lock_timeout='5s'")
        cursor.execute('LOCK TABLE public.portfolio_proyecto, public.portfolio_tecnologia, '
                       'public.portfolio_proyecto_technologies IN SHARE ROW EXCLUSIVE MODE')
    if snapshot('public') != before:
        raise RuntimeError('Portfolio changed during preparation; nothing committed.')
    call_command('load_aubar_bot', schema='public', publish=True)
    after = snapshot('public')
    allowed = {'portfolio_proyecto', 'portfolio_tecnologia', 'portfolio_proyecto_technologies'}
    for table, rows in before.items():
        current = {row['id']: row for row in after[table]}
        if any(current.get(row['id']) != row for row in rows):
            raise RuntimeError('Existing rows changed; rolling back.')
        if table not in allowed and rows != after[table]:
            raise RuntimeError('Unrelated table changed; rolling back.')
    if private_before is not None and snapshot('portfolio_django') != private_before:
        raise RuntimeError('Private schema changed; rolling back.')
    call_command('load_aubar_bot', schema='public', publish=True)
    if snapshot('public') != after:
        raise RuntimeError('Repeated load changed data; rolling back.')
    if not args.apply:
        transaction.set_rollback(True)

report = {
    'target': args.target, 'applied': args.apply, 'schema': 'public',
    'backup': str(backup.relative_to(ROOT)), 'beforeDigest': digest(before),
    'afterDigest': digest(after if args.apply else before),
    'existingRowsUnchanged': True, 'privateSchemaUnchanged': True,
    'idempotent': True,
    'projectsBefore': len(before['portfolio_proyecto']),
    'projectsAfter': len((after if args.apply else before)['portfolio_proyecto']),
}
report_path = ROOT / 'reports' / f'aubar-bot-{args.target}-publication.json'
report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report))
