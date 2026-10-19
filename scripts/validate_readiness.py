"""TK17: verify real HTTP readiness, a refused DB connection and recovery."""
import json
import os
import platform
import socket
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from run_regression import (
    BACKEND_ROOT, REPORTS_ROOT, create_e2e_database, drop_e2e_database,
    environment_for, git_metadata, require_configuration, run_command, stop_process,
)

CANARY = 'TK17_SYNTHETIC_PRIVATE_CANARY'


def serve():
    # A test-only WSGI server avoids runserver's migration check: an unavailable
    # database must not prevent the app from serving its own 503 readiness.
    sys.path.insert(0, str(BACKEND_ROOT))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    from django.core.wsgi import get_wsgi_application
    from wsgiref.simple_server import make_server, WSGIRequestHandler

    class QuietHandler(WSGIRequestHandler):
        def log_message(self, format, *args):
            # stdlib access logging bypasses Django's formatter and includes URLs.
            pass

    with make_server('127.0.0.1', 8766, get_wsgi_application(), handler_class=QuietHandler) as server:
        server.serve_forever()


def probe():
    request = Request('http://127.0.0.1:8766/health/?token=' + CANARY, headers={
        'Authorization': 'Bearer ' + CANARY, 'Cookie': 'sessionid=' + CANARY,
    })
    try:
        response = urlopen(request, timeout=10)
    except HTTPError as error:
        response = error
    with response:
        return {'status': response.code, 'json': json.loads(response.read()),
                'cacheControl': response.headers.get('Cache-Control')}


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    development, test = require_configuration()
    with socket.socket() as check:
        check.bind(('127.0.0.1', 8766))
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    folder = REPORTS_ROOT / f'TK17-{run_id}'
    folder.mkdir(parents=True)
    report = {
        'task': 'TK17', 'case': 'BE-CP24', 'startedAt': datetime.now(timezone.utc).isoformat(),
        'revision': git_metadata(BACKEND_ROOT), 'result': 'failed', 'steps': [],
        'environment': {'platform': platform.platform(), 'python': platform.python_version(),
                        'debug': False, 'server': 'stdlib WSGI, loopback only; raw access logs disabled'},
        'evidenceDirectory': str(folder.relative_to(BACKEND_ROOT)), 'probes': [],
    }
    database, process = None, None
    try:
        import django
        import psycopg
        report['environment']['django'] = django.get_version()
        database = create_e2e_database(development, test)
        report['temporaryDatabase'] = database
        env = environment_for(database, development)
        env['DJANGO_CORS_ALLOWED_ORIGINS'] = ''
        with psycopg.connect(dbname=database, user=env['POSTGRES_USER'],
                             password=env['POSTGRES_PASSWORD'],
                             host=env.get('POSTGRES_HOST', '127.0.0.1'),
                             port=env.get('POSTGRES_PORT', '5432')) as db:
            report['environment']['postgresql'] = db.execute('SHOW server_version').fetchone()[0]
        # No migrations or seed needed: the readiness query does not read app tables.
        with socket.socket() as refused_database:
            refused_database.bind(('127.0.0.1', 0))
            refused_port = refused_database.getsockname()[1]
            for phase in ('available', 'unavailable', 'recovered'):
                phase_env = env.copy()
                if phase == 'unavailable':
                    phase_env.update(POSTGRES_HOST='127.0.0.1', POSTGRES_PORT=str(refused_port),
                                     POSTGRES_USER=CANARY, POSTGRES_PASSWORD=CANARY)
                log_path = folder / f'{phase}.log'
                with log_path.open('w', encoding='utf-8') as output:
                    process = subprocess.Popen(
                        [sys.executable, str(BACKEND_ROOT / 'scripts/validate_readiness.py'), '--serve'],
                        cwd=BACKEND_ROOT, env=phase_env, stdout=output, stderr=subprocess.STDOUT,
                    )
                deadline = time.monotonic() + 30
                while True:
                    if process.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError('WSGI test server failed to start; inspect phase log.')
                    try:
                        with socket.create_connection(('127.0.0.1', 8766), timeout=0.2):
                            break
                    except OSError:
                        time.sleep(0.05)
                actual = probe()
                stop_process(process)
                process = None
                logs = log_path.read_text(encoding='utf-8')
                expected = 503 if phase == 'unavailable' else 200
                if actual['status'] != expected or actual['json'] != {
                    'status': 'unavailable' if phase == 'unavailable' else 'ok'
                }:
                    raise RuntimeError('Readiness returned an unexpected public response.')
                if CANARY in logs or CANARY in json.dumps(actual):
                    raise RuntimeError('Synthetic private canary leaked into output.')
                records = [json.loads(line) for line in logs.splitlines() if line.strip()]
                if phase == 'unavailable' and not any(
                    r.get('errorType') == 'OperationalError' for r in records
                ):
                    raise RuntimeError('Unavailable DB did not emit a safe diagnostic.')
                report['probes'].append({'phase': phase, **actual, 'safeLogs': records})
                print(f'{phase}: HTTP {actual["status"]}; private canary absent', flush=True)
        test_env = env.copy()
        test_env['POSTGRES_TEST_DB'] = f'portfolio_suite_{uuid.uuid4().hex[:12]}'
        report['validationTestDatabase'] = test_env['POSTGRES_TEST_DB']
        run_command([sys.executable, 'manage.py', 'test', '--noinput'],
                    BACKEND_ROOT, test_env, report, 'backend-postgresql-regression')
        report['result'] = 'passed'
    except Exception as error:
        report['failure'] = str(error)
        raise
    finally:
        stop_process(process)
        if database:
            try:
                drop_e2e_database(database)
                report['databaseCleanedUp'] = True
            except Exception:
                report['result'] = 'failed'
                report['databaseCleanedUp'] = False
        report['finishedAt'] = datetime.now(timezone.utc).isoformat()
        report_path = REPORTS_ROOT / f'TK17-readiness-{run_id}.json'
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'Report: {report_path}')
    return 0 if report['result'] == 'passed' else 1


if __name__ == '__main__':
    if sys.argv[1:] == ['--serve']:
        serve()
    else:
        raise SystemExit(main())
