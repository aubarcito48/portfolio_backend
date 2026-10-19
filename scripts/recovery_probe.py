"""Private child process for TK19; refuses databases outside the disposable cluster."""
import hashlib
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import django

django.setup()

from django.apps import apps
from django.db import connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import Client
from psycopg import sql


SCHEMA = 'portfolio_django'


def guard():
    import portfolio
    assert Path(portfolio.__file__).resolve().is_relative_to(Path(os.environ['TK19_CODE_ROOT']).resolve())
    db = connection.settings_dict
    assert connection.vendor == 'postgresql'
    assert db['HOST'] == '127.0.0.1'
    assert db['NAME'] == os.environ['TK19_DATABASE']
    assert db['NAME'].startswith('portfolio_recovery_')
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('data_directory')")
        actual = Path(cursor.fetchone()[0]).resolve()
    assert actual == Path(os.environ['TK19_DATA_DIRECTORY']).resolve()


def seed():
    """Replace only the migrations' content in the isolated SOURCE database."""
    assert os.environ['TK19_DATABASE'].startswith('portfolio_recovery_source_')
    from portfolio.models import (
        Perfil, Tecnologia, Experiencia, Formacion, Proyecto, EnlaceProyecto, Enlace,
    )
    with transaction.atomic():
        for model in (EnlaceProyecto, Proyecto, Tecnologia, Experiencia, Formacion, Enlace, Perfil):
            model.objects.all().delete()
        profile = Perfil.objects.create(
            name='Recovery Fixture', professional_title='Synthetic engineer',
            biography='Deterministic synthetic content: á, ñ, 日本語.',
            location='Test environment', image_url='/assets/recovery.png', is_published=True,
        )
        # Preserve microseconds: the SQL comparison must not truncate timestamps.
        Perfil.objects.filter(pk=profile.pk).update(
            updated_at=datetime(2026, 1, 2, 3, 4, 5, 123456, tzinfo=timezone.utc))
        technologies = [Tecnologia.objects.create(
            name=f'Recovery Technology {i}', category='Recovery',
            url=f'https://example.test/technology/{i}', order=i, is_published=i < 2,
        ) for i in range(3)]
        for i, published in ((1, True), (2, False)):
            project = Proyecto.objects.create(
                title=f'Recovery Project {i}', slug=f'recovery-project-{i}',
                summary='Synthetic recovery summary', description='Synthetic description.',
                project_type='Recovery test', order=i, is_published=published,
            )
            project.technologies.set(technologies if published else technologies[1:])
            EnlaceProyecto.objects.create(project=project, label=f'Recovery link {i}',
                                         url=f'https://example.test/project/{i}')
            Experiencia.objects.create(
                title=f'Recovery Experience {i}', organization='Synthetic organization',
                description='Synthetic only.', start_date=date(2025, 1, 1),
                is_current=True, order=i, is_published=published,
            )
            Formacion.objects.create(
                name=f'Recovery Education {i}', institution='Synthetic institution',
                type='study', status='in_progress', start_date=date(2025, 1, 1),
                order=i, is_published=published,
            )
            Enlace.objects.create(label=f'Recovery Contact {i}', type=f'recovery-{i}',
                                 url=f'https://example.test/contact/{i}',
                                 order=i, is_published=published)


def digest(value):
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False,
                         separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def inspect():
    result = {}
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
            cursor.execute('SELECT current_schema()')
            assert cursor.fetchone()[0] == SCHEMA
            cursor.execute("""SELECT tablename FROM pg_tables
                WHERE schemaname=%s ORDER BY tablename""", [SCHEMA])
            names = [row[0] for row in cursor.fetchall()]
            tables = {}
            for name in names:
                cursor.execute(sql.SQL('SELECT to_jsonb(t) FROM {}.{} t').format(
                    sql.Identifier(SCHEMA), sql.Identifier(name)))
                rows = [row[0] for row in cursor.fetchall()]
                rows.sort(key=lambda row: json.dumps(row, sort_keys=True, ensure_ascii=False))
                tables[name] = {'count': len(rows), 'allValuesSha256': digest(rows)}
            cursor.execute('SELECT sequencename FROM pg_sequences WHERE schemaname=%s ORDER BY 1',
                           [SCHEMA])
            names = [row[0] for row in cursor.fetchall()]
            sequences = {}
            for name in names:
                cursor.execute(sql.SQL('SELECT last_value, is_called FROM {}.{}').format(
                    sql.Identifier(SCHEMA), sql.Identifier(name)))
                sequences[name] = cursor.fetchone()
        result['tables'] = tables
        result['sequences'] = sequences
        result['counts'] = {model._meta.label_lower: model._base_manager.count()
                            for model in apps.get_app_config('portfolio').get_models()}
        project = apps.get_model('portfolio', 'Proyecto')
        result['projectTechnologyRelations'] = project.technologies.through.objects.count()
        executor = MigrationExecutor(connection)
        result['pendingMigrations'] = len(executor.migration_plan(executor.loader.graph.leaf_nodes()))
        assert result['pendingMigrations'] == 0
        client = Client()
        endpoints = {}
        for path in ('/health/', '/api/v1/perfil/', '/api/v1/tecnologias/',
                     '/api/v1/experiencias/', '/api/v1/formacion/',
                     '/api/v1/proyectos/', '/api/v1/enlaces/',
                     '/api/v1/proyectos/recovery-project-1/',
                     '/api/v1/proyectos/recovery-project-2/'):
            response = client.get(path, HTTP_HOST='localhost', HTTP_X_FORWARDED_PROTO='https')
            expected = 404 if path.endswith('recovery-project-2/') else 200
            assert response.status_code == expected, path
            payload = response.json()
            if path == '/api/v1/proyectos/':
                assert payload['count'] == 1
                assert len(payload['results'][0]['technologies']) == 2
            if path in ('/api/v1/experiencias/', '/api/v1/formacion/', '/api/v1/enlaces/'):
                assert payload['count'] == 1
            if path == '/api/v1/tecnologias/':
                assert payload['count'] == 2
            endpoints[path] = {'status': response.status_code, 'payloadSha256': digest(payload)}
        result['endpoints'] = endpoints
    return result


if __name__ == '__main__':
    try:
        guard()
        if sys.argv[1] == 'seed':
            seed()
        else:
            result = inspect()
            Path(sys.argv[2]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print('PASS: isolated recovery probe ' + sys.argv[1], flush=True)
    except Exception as error:
        print('FAIL: recovery probe (' + type(error).__name__ + '); details withheld.', flush=True)
        raise SystemExit(1)
