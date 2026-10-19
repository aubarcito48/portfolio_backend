"""Read-only, secret-free database verification from the running service."""
import json
import os
from pathlib import Path

from django.apps import apps
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connection, transaction

from portfolio.transfer import fixture_summary


class Command(BaseCommand):
    help = 'Verify the active database and compare portfolio against the transfer report (read-only).'

    def add_arguments(self, parser):
        parser.add_argument('--report', default='reports/supabase-transfer-execution.json')

    def handle(self, *args, **options):
        baseline = json.loads(Path(options['report']).read_text(encoding='utf-8'))['summary']
        db = connection.settings_dict
        result = {
            'runningOnRender': os.getenv('RENDER') == 'true',
            'postgresqlBackend': connection.vendor == 'postgresql',
            'expectedSupabaseHost': db.get('HOST') == 'aws-0-us-east-1.pooler.supabase.com',
            'expectedSupabaseProjectUser': db.get('USER') == 'postgres.lacgvfrppovxounlzzmp',
            'expectedDatabaseName': db.get('NAME') == 'postgres',
            'expectedSessionPoolerPort': str(db.get('PORT')) == '5432',
        }
        if not result['postgresqlBackend']:
            self.stdout.write(json.dumps(result))
            raise CommandError('Expected PostgreSQL; no database query was executed.')
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
                    cursor.execute('SELECT current_schema()')
                    result['expectedPrivateSchema'] = cursor.fetchone()[0] == 'portfolio_django'
                    # With a session pooler pg_stat_ssl describes the pooler's
                    # server connection, not Django's TLS connection to it.
                    result['sslActive'] = bool(connection.connection.pgconn.ssl_in_use)
                records = [obj for model in apps.get_app_config('portfolio').get_models()
                           for obj in model._base_manager.all()]
                actual = fixture_summary(json.loads(serializers.serialize('json', records)))
                result['counts'] = actual['counts']
                result['projectTechnologyRelations'] = actual['projectTechnologyRelations']
                result['countsMatchTransfer'] = actual['counts'] == baseline['counts']
                result['relationsCountMatchesTransfer'] = (
                    actual['projectTechnologyRelations'] == baseline['projectTechnologyRelations'])
                result['serializedValuesAndRelationsMatchTransfer'] = actual == baseline
        except DatabaseError:
            raise CommandError('Read-only database check failed; connection details withheld.') from None
        checks = [value for key, value in result.items()
                  if isinstance(value, bool) and key != 'runningOnRender']
        result['passed'] = all(checks)
        self.stdout.write(json.dumps(result, indent=2))
        if not result['passed']:
            raise CommandError('Database identity or portfolio differs from the transfer baseline. No data changed.')
