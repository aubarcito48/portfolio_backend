import importlib
import json
import os
import subprocess
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command
from django.db import DatabaseError, connection, transaction
from django.db.migrations.operations.special import RunPython
from psycopg import sql

from portfolio.transfer import canonical_fixture, fixture_summary


# Only initial portfolio content is skipped for a NEW import installation.
# Schema migrations and 0010_content_editors run unchanged. No file is edited.
CONTENT_SEEDS = {
    '0002_initial_profile': 'create_initial_profile',
    '0004_initial_technologies': 'create_initial_technologies',
    '0008_initial_projects': 'create_initial_projects',
    '0009_enlace': 'create_initial_links',
}


def inventory():
    with connection.cursor() as cursor:
        cursor.execute("""SELECT n.nspname, c.relname, c.relkind
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname NOT LIKE 'pg_%%' AND n.nspname <> 'information_schema'
              AND c.relkind IN ('r','p','v','m','S','f') ORDER BY 1,2""")
        objects = cursor.fetchall()
        cursor.execute('SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname=%s)',
                       [settings.SUPABASE_MIGRATION_SCHEMA])
        exists = cursor.fetchone()[0]
    return {'targetSchemaExists': exists, 'objects': objects,
            'djangoObjectsOutsideTarget': [(schema, name) for schema, name, kind in objects
                if schema != settings.SUPABASE_MIGRATION_SCHEMA
                and name.startswith(('portfolio_', 'django_', 'auth_'))]}


def private_file(path, *, must_be_new=False):
    root = (settings.BASE_DIR / 'backups').resolve()
    path = Path(path).resolve()
    if not path.is_relative_to(root) or path == root:
        raise CommandError('Transfer artifacts must stay inside the ignored backups/ directory.')
    if must_be_new and path.exists():
        raise CommandError('Refusing to overwrite an existing artifact.')
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


class Command(BaseCommand):
    help = 'Prepare portfolio transfer: backup/export local; preflight/import/compare target.'

    def add_arguments(self, parser):
        parser.add_argument('action', choices=['backup', 'export', 'preflight', 'import-new', 'compare'])
        parser.add_argument('--file', required=True)
        parser.add_argument('--pg-dump')

    def handle(self, *args, **options):
        try:
            return self.transfer(*args, **options)
        except DatabaseError:
            raise CommandError('Database operation failed; raw diagnostics withheld to protect secrets.') from None

    def transfer(self, *args, **options):
        action = options['action']
        target = getattr(settings, 'SUPABASE_MIGRATION_SCHEMA', None)
        if action in {'backup', 'export'} and target:
            raise CommandError('This action must use LOCAL settings, never Supabase.')
        if action in {'preflight', 'import-new', 'compare'} and not target:
            raise CommandError('This action requires explicit settings_supabase.')
        path = private_file(options['file'], must_be_new=action in {'backup', 'export', 'preflight'})
        if action == 'backup':
            if not options['pg_dump']:
                raise CommandError('--pg-dump must point to the installed PostgreSQL pg_dump executable.')
            db = connection.settings_dict
            if db['HOST'] not in {'localhost', '127.0.0.1', '::1'}:
                raise CommandError('Local backup refuses a non-loopback source host.')
            env = os.environ.copy()
            env.update(PGHOST=db['HOST'], PGPORT=str(db['PORT']), PGDATABASE=db['NAME'],
                       PGUSER=db['USER'], PGPASSWORD=db['PASSWORD'],
                       PGPASSFILE=str(path.parent / 'unused-pgpass'))
            env.pop('PGSERVICE', None)
            result = subprocess.run([options['pg_dump'], '--format=custom', '--no-password',
                                     '--file', str(path)], env=env, capture_output=True)
            if result.returncode:
                raise CommandError('Local pg_dump failed. Raw output withheld to protect credentials.')
            self.stdout.write('LOCAL full backup created; never restore it into Supabase automatically.')
            return
        if action == 'preflight':
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute('SET TRANSACTION READ ONLY')
                result = inventory()
            path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
            self.stdout.write('TARGET catalog inspected read-only; report saved privately.')
            if result['targetSchemaExists'] or result['djangoObjectsOutsideTarget']:
                raise CommandError('Existing Django schema/objects detected. STOP; no changes were made.')
            return
        if action == 'export':
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
                # dumpdata --output uses the platform locale on Windows;
                # explicitly provide a UTF-8 stream for a portable fixture.
                with path.open('w', encoding='utf-8') as output:
                    call_command('dumpdata', 'portfolio', use_base_manager=True,
                                 indent=2, stdout=output, verbosity=0)
            summary = fixture_summary(json.loads(path.read_text(encoding='utf-8')))
            self.stdout.write(json.dumps(summary))
            return
        records = canonical_fixture(json.loads(path.read_text(encoding='utf-8')))
        expected = fixture_summary(records)
        if action == 'import-new':
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_advisory_xact_lock(hashtext('portfolio_fresh_import'))")
                existing = inventory()
                if existing['targetSchemaExists'] or existing['djangoObjectsOutsideTarget']:
                    raise CommandError('Target is not a fresh installation. Import refused without changes.')
                with connection.cursor() as cursor:
                    cursor.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(target)))
                    cursor.execute(sql.SQL('REVOKE ALL ON SCHEMA {} FROM PUBLIC').format(sql.Identifier(target)))
                    cursor.execute(sql.SQL('SET LOCAL search_path TO {}, pg_catalog').format(sql.Identifier(target)))
                with ExitStack() as stack:
                    for name, function in CONTENT_SEEDS.items():
                        module = importlib.import_module('portfolio.migrations.' + name)
                        seeds = [op for op in module.Migration.operations if isinstance(op, RunPython)
                                 and op.code.__name__ == function]
                        if len(seeds) != 1:
                            raise CommandError('Initial data migrations changed; review the import plan.')
                        stack.enter_context(patch.object(seeds[0], 'code', RunPython.noop))
                    call_command('migrate', interactive=False, verbosity=0)
                try:
                    call_command('loaddata', str(path), verbosity=0)
                except Exception:
                    raise CommandError('Fixture import failed; the new installation is rolled back. '
                                       'Private values are not printed.') from None
                self.compare(expected)
            self.stdout.write('TARGET new private schema migrated/imported and verified atomically.')
        else:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
                self.compare(expected)

    def compare(self, expected):
        from django.core import serializers
        from django.apps import apps
        # Include drafts, exact PK/field values, additional-link FKs and M2M IDs.
        with transaction.atomic():
            records = [obj for model in apps.get_app_config('portfolio').get_models()
                       for obj in model._base_manager.all()]
            actual = fixture_summary(json.loads(serializers.serialize('json', records)))
        if actual != expected:
            raise CommandError('Counts, values or relationships differ. No private values printed.')
        self.stdout.write(json.dumps({'match': True, **actual}))
