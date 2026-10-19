"""TK19: disposable PostgreSQL cluster, full restore and compatible code rollback.

Never loads .env or accepts connection arguments to an existing database.
Private artifacts are retained under ignored backups/; the cluster is stopped.
"""
import argparse
import csv
import hashlib
import io
import json
import os
import secrets
import socket
import stat
import subprocess
import sys
import tarfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from psycopg import sql


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'portfolio_django'


class ExistingRecoveryObjects(RuntimeError):
    pass


def require_empty_target(connection, expected_directory):
    actual = connection.execute('SHOW data_directory').fetchone()[0]
    if Path(actual).resolve() != expected_directory.resolve():
        raise RuntimeError('Destination is outside the disposable cluster')
    objects = connection.execute("""SELECT count(*) FROM pg_class c JOIN pg_namespace n
        ON n.oid=c.relnamespace WHERE n.nspname NOT LIKE 'pg_%'
        AND n.nspname <> 'information_schema' AND c.relkind IN ('r','p','S','v','m','f')""").fetchone()[0]
    if objects:
        raise ExistingRecoveryObjects('Refusing restore into a nonempty database')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protect(folder):
    if os.name == 'nt':
        identity = subprocess.check_output(['whoami', '/user', '/fo', 'csv', '/nh'], text=True)
        sid = next(csv.reader(io.StringIO(identity.strip())))[1]
        subprocess.run(['icacls', str(folder), '/inheritance:r', '/grant:r',
                        f'*{sid}:(OI)(CI)F', '*S-1-5-18:(OI)(CI)F'],
                       capture_output=True, check=True)
    else:
        folder.chmod(stat.S_IRWXU)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pg-bin', default='C:/Program Files/PostgreSQL/18/bin')
    parser.add_argument('--rollback-ref', default='42e68bb46b2d245dec9b21167dd692cd0ca729bb')
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    folder = ROOT / 'backups' / f'recovery-{stamp}-{uuid.uuid4().hex[:6]}'
    folder.mkdir(parents=True, exist_ok=False)
    protect(folder)
    data = folder / 'cluster'
    extension = '.exe' if os.name == 'nt' else ''
    pg_bin = Path(args.pg_bin)
    binary = lambda name: str(pg_bin / (name + extension))
    for name in ('initdb', 'pg_ctl', 'pg_dump', 'pg_restore'):
        if not Path(binary(name)).is_file():
            raise RuntimeError('PostgreSQL tools missing; specify --pg-bin.')
    report_path = ROOT / 'reports' / f'TK19-recovery-{stamp}.json'
    report = {'case': 'BE-CP26', 'startedAtUtc': datetime.now(timezone.utc).isoformat(),
              'artifacts': str(folder.relative_to(ROOT)), 'steps': [], 'result': 'running',
              'sourceAndTarget': 'two new databases in a disposable loopback-only cluster',
              'productionContacted': False, 'credentialsParsedFromEnvFiles': False,
              'privateStoragePermissionsApplied': True,
              'workingTreeContainsRecoveryImplementation': True,
              'sourceFileSha256': {name: sha(ROOT / 'scripts' / name)
                                   for name in ('validate_recovery.py', 'recovery_probe.py')}}
    original_env_hashes = {name: sha(ROOT / name) for name in ('.env', '.env.supabase')
                           if (ROOT / name).is_file()}
    # Do not inherit any database/service credentials, settings or search paths.
    env = {key: value for key, value in os.environ.items()
           if not key.upper().startswith(('PG', 'POSTGRES', 'DJANGO', 'SUPABASE', 'PORTFOLIO', 'TK19'))
           and key.upper() not in {'DATABASE_URL', 'PYTHONPATH', 'PYTHONHOME'}}
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    password = secrets.token_urlsafe(32)
    env.update(PGHOST='127.0.0.1', PGPORT=str(port), PGUSER='recovery_runner',
               PGPASSWORD=password, PGSSLMODE='disable', PGDATABASE='postgres',
               PGPASSFILE=str(folder / 'no-pgpass'), PYTHON_DOTENV_DISABLED='1',
               PYTHONIOENCODING='utf-8', DJANGO_SETTINGS_MODULE='recovery_settings',
               DJANGO_SECRET_KEY=secrets.token_urlsafe(64), DJANGO_ENVIRONMENT='production',
               DJANGO_DEBUG='False', DJANGO_ALLOWED_HOSTS='localhost,127.0.0.1',
               DJANGO_CORS_ALLOWED_ORIGINS='', DJANGO_CSRF_TRUSTED_ORIGINS='',
               POSTGRES_HOST='127.0.0.1', POSTGRES_PORT=str(port),
               POSTGRES_USER='recovery_runner', POSTGRES_PASSWORD=password,
               POSTGRES_TEST_DB='portfolio_recovery_tests_not_used',
               TK19_DATA_DIRECTORY=str(data), TK19_CODE_ROOT=str(ROOT),
               PYTHONPATH=str(folder) + os.pathsep + str(ROOT))
    (folder / 'recovery_settings.py').write_text('''from config.settings import *
from django.db.backends.signals import connection_created
def select_schema(sender, connection, **kwargs):
    with connection.cursor() as cursor:
        cursor.execute('SET search_path TO portfolio_django, pg_catalog')
connection_created.connect(select_schema, weak=False, dispatch_uid='tk19_private_schema')
''', encoding='utf-8')

    def run(name, command, *, environment=None, cwd=ROOT):
        print('>>> ' + name, flush=True)
        started = time.monotonic()
        log = folder / (name + '.log')
        # PostgreSQL can inherit pipe handles on Windows. A real log file lets
        # pg_ctl finish without waiting for the server to close inherited pipes.
        with log.open('wb') as output:
            outcome = subprocess.run(command, env=environment or env, cwd=cwd,
                                     stdout=output, stderr=subprocess.STDOUT, timeout=180)
        report['steps'].append({'name': name, 'exitCode': outcome.returncode,
                                'seconds': round(time.monotonic() - started, 3)})
        if outcome.returncode:
            raise RuntimeError('Step failed: ' + name + '; raw output retained privately.')
        return log.read_bytes()

    def database_env(name):
        return env | {'POSTGRES_DB': name, 'PGDATABASE': name, 'TK19_DATABASE': name}

    def connect(name):
        return psycopg.connect(host='127.0.0.1', port=port, user='recovery_runner',
                               password=password, dbname=name, connect_timeout=5, autocommit=True)

    started_cluster = False
    pwfile = folder / 'init-password'
    try:
        report['gitCommit'] = run('current-revision', ['git', 'rev-parse', 'HEAD']).decode().strip()
        revision = run('rollback-revision', ['git', 'rev-parse', '--verify',
                                           args.rollback_ref + '^{commit}']).decode().strip()
        report['rollbackCommit'] = revision
        run('same-models-and-migrations', ['git', 'diff', '--exit-code', revision, 'HEAD',
                                         '--', 'portfolio/models.py', 'portfolio/migrations'])
        # Reject uncommitted changes to schema/model code too.
        run('clean-models-and-migrations', ['git', 'diff', 'HEAD', '--exit-code',
                                          '--', 'portfolio/models.py', 'portfolio/migrations'])
        untracked = run('no-untracked-models-or-migrations',
                        ['git', 'ls-files', '--others', '--exclude-standard', '--',
                         'portfolio/models.py', 'portfolio/migrations'])
        if untracked.strip():
            raise RuntimeError('Untracked model/migration files require review')
        old = folder / 'previous-code'
        run('archive-previous-code', ['git', 'archive', '--format=tar',
                                     '--output', str(folder / 'previous-code.tar'), revision])
        old.mkdir()
        with tarfile.open(folder / 'previous-code.tar') as archive:
            archive.extractall(old, filter='data')
        report['versions'] = {name: run(name + '-version', [binary(name), '--version']).decode().strip()
                              for name in ('pg_dump', 'pg_restore')}
        report['versions']['python'] = sys.version.split()[0]
        import django
        report['versions']['django'] = django.get_version()
        pwfile.write_text(password + '\n', encoding='utf-8')
        run('init-cluster', [binary('initdb'), '-D', str(data), '-U', 'recovery_runner',
                             '--auth=scram-sha-256', '--pwfile', str(pwfile),
                             '--encoding=UTF8', '--locale=C'])
        pwfile.unlink()
        # Mark before starting so a timeout still triggers a shutdown attempt.
        started_cluster = True
        run('start-cluster', [binary('pg_ctl'), '-D', str(data), '-l', str(folder / 'postgres.log'),
                              '-o', f'-h 127.0.0.1 -p {port}', '-w', 'start'])
        token = uuid.uuid4().hex[:10]
        source = 'portfolio_recovery_source_' + token
        target = 'portfolio_recovery_restored_' + token
        with connect('postgres') as admin:
            assert Path(admin.execute("SHOW data_directory").fetchone()[0]).resolve() == data.resolve()
            for name in (source, target):
                admin.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0').format(sql.Identifier(name)))
        source_env, target_env = database_env(source), database_env(target)
        with connect(source) as source_connection:
            source_connection.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(SCHEMA)))
        python = sys.executable
        run('migrate-synthetic-source', [python, '-B', 'manage.py', 'migrate', '--noinput'], environment=source_env)
        probe_script = str(ROOT / 'scripts/recovery_probe.py')
        run('seed-known-data', [python, '-B', probe_script, 'seed'], environment=source_env)
        before = folder / 'source-before.json'
        run('reference-before-backup', [python, '-B', probe_script, 'inspect', str(before)], environment=source_env)
        dump = folder / 'postgresql-full.dump'
        run('pg-dump', [binary('pg_dump'), '--format=custom', '--no-password',
                        '--file', str(dump)], environment=source_env)
        report['backupSha256'] = sha(dump)
        report['backupBytes'] = dump.stat().st_size
        run('verify-archive-catalog', [binary('pg_restore'), '--list', str(dump)])
        # Recheck the destination on this fresh cluster immediately before restore.
        with connect(target) as target_connection:
            require_empty_target(target_connection, data)
        run('restore-new-isolated-database', [binary('pg_restore'), '--no-password', '--no-owner',
            '--no-privileges', '--exit-on-error', '--single-transaction', '--dbname', target, str(dump)],
            environment=target_env)
        # Exercise the refusal against the populated recovery target, without
        # calling pg_restore again. Subsequent comparisons prove it is unchanged.
        with connect(target) as target_connection:
            try:
                require_empty_target(target_connection, data)
            except ExistingRecoveryObjects:
                report['nonemptyDestinationRejectedBeforeRestore'] = True
            else:
                raise RuntimeError('Nonempty destination guard did not reject the target')
        restored = folder / 'restored-current.json'
        run('django-restored-current', [python, '-B', probe_script, 'inspect', str(restored)], environment=target_env)
        run('current-code-system-check', [python, '-B', 'manage.py', 'check'], environment=target_env)
        old_env = target_env | {'PYTHONPATH': str(folder) + os.pathsep + str(old),
                                'TK19_CODE_ROOT': str(old)}
        # Run a copy of the probe beside the settings so Python does not import
        # the current checkout's scripts directory as the old application.
        old_probe = folder / 'recovery_probe.py'
        old_probe.write_bytes((ROOT / 'scripts/recovery_probe.py').read_bytes())
        previous = folder / 'restored-previous.json'
        run('previous-code-system-check', [python, '-B', 'manage.py', 'check'], environment=old_env, cwd=old)
        run('django-compatible-rollback', [python, '-B', str(old_probe), 'inspect', str(previous)],
            environment=old_env, cwd=old)
        after = folder / 'source-after.json'
        run('source-unchanged', [python, '-B', probe_script, 'inspect', str(after)], environment=source_env)
        reference = json.loads(before.read_text(encoding='utf-8'))
        for path in (restored, previous, after):
            assert json.loads(path.read_text(encoding='utf-8')) == reference, 'Recovery comparison differs'
        report.update(counts=reference['counts'], projectTechnologyRelations=reference['projectTechnologyRelations'],
                      tablesCompared=len(reference['tables']), sequencesCompared=len(reference['sequences']),
                      endpoints=reference['endpoints'], allTableValuesAndSequencesMatch=True,
                      exactMicrosecondsCompared=True, rollbackSameSchemaVerified=True,
                      oldCodeQueriesRestoredData=True, sourceUnchanged=True,
                      rawValuesPublished=False, result='passed')
    except Exception as error:
        report['result'] = 'failed'
        report['failureType'] = type(error).__name__
        print('FAIL: recovery stopped; private diagnostics retained.', flush=True)
    finally:
        if pwfile.exists():
            pwfile.unlink()
        if started_cluster:
            try:
                if (data / 'postmaster.pid').exists():
                    run('stop-disposable-cluster', [binary('pg_ctl'), '-D', str(data), '-m', 'fast', '-w', 'stop'])
                report['clusterStopped'] = True
            except Exception:
                report['clusterStopped'] = False
                report['result'] = 'failed'
        report['envFilesUnchanged'] = all(sha(ROOT / name) == value for name, value in original_env_hashes.items())
        if not report['envFilesUnchanged']:
            report['result'] = 'failed'
        report['finishedAtUtc'] = datetime.now(timezone.utc).isoformat()
        report_path.parent.mkdir(exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report, indent=2), flush=True)
    return 0 if report['result'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
