import json
import hashlib
import os
import socket
import shutil
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import psycopg
from django.utils.version import get_version
from dotenv import load_dotenv
from psycopg import sql


BACKEND_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = BACKEND_ROOT.parent / 'cv-proyecto'
REPORTS_ROOT = BACKEND_ROOT / 'reports'
API_URL = 'http://localhost:8000/api/v1/'
FRONTEND_URL = 'http://127.0.0.1:4301/'
BACKEND_PORT = 8000
FRONTEND_PORT = 4301


def require_configuration():
    load_dotenv(BACKEND_ROOT / '.env')
    required = (
        'DJANGO_SECRET_KEY',
        'POSTGRES_DB',
        'POSTGRES_USER',
        'POSTGRES_PASSWORD',
    )
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            'Faltan variables requeridas en el entorno o .env: '
            + ', '.join(missing)
        )

    development_database = os.environ['POSTGRES_DB']
    test_database = os.getenv('POSTGRES_TEST_DB', f'test_{development_database}')
    if test_database == development_database:
        raise RuntimeError('La base de pruebas debe ser distinta de desarrollo.')
    return development_database, test_database


def ensure_ports_available():
    for port in (BACKEND_PORT, FRONTEND_PORT):
        with socket.socket() as probe:
            try:
                probe.bind(('127.0.0.1', port))
            except OSError as error:
                raise RuntimeError(
                    f'El puerto {port} ya está ocupado; no se iniciaron servidores.'
                ) from error


def create_e2e_database(development_database, test_database):
    connection_options = {
        'dbname': 'postgres',
        'user': os.environ['POSTGRES_USER'],
        'password': os.environ['POSTGRES_PASSWORD'],
        'host': os.getenv('POSTGRES_HOST', '127.0.0.1'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'connect_timeout': 5,
    }

    with psycopg.connect(**connection_options, autocommit=True) as admin_connection:
        for _ in range(5):
            database_name = f'portfolio_e2e_{uuid.uuid4().hex[:12]}'
            if database_name in {development_database, test_database}:
                continue
            exists = admin_connection.execute(
                'SELECT 1 FROM pg_database WHERE datname = %s',
                (database_name,),
            ).fetchone()
            if exists is None:
                admin_connection.execute(
                    sql.SQL('CREATE DATABASE {}').format(
                        sql.Identifier(database_name)
                    )
                )
                return database_name

    raise RuntimeError('No se pudo generar un nombre de base E2E temporal único.')


def environment_for(database_name, development_database):
    environment = os.environ.copy()
    environment.update(
        {
            'DJANGO_ENVIRONMENT': 'test',
            'DJANGO_DEBUG': 'False',
            'DJANGO_ALLOWED_HOSTS': 'localhost,127.0.0.1',
            'DJANGO_CORS_ALLOWED_ORIGINS': 'http://127.0.0.1:4301',
            'POSTGRES_DB': database_name,
            'PORTFOLIO_E2E_DATABASE': database_name,
            'PORTFOLIO_DEVELOPMENT_DATABASE': development_database,
            'PYTHONIOENCODING': 'utf-8',
        }
    )
    return environment


def run_command(command, cwd, environment, report, name):
    print(f'>>> {name}', flush=True)
    started = time.monotonic()
    result = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        check=False,
    )
    step = {
        'name': name,
        'command': command,
        'exitCode': result.returncode,
        'durationSeconds': round(time.monotonic() - started, 3),
        'stdout': result.stdout,
        'stderr': result.stderr,
    }
    match = re.search(r'Ran (\d+) tests?', result.stderr)
    if match:
        step['testCount'] = int(match.group(1))
    if name == 'frontend-unit-suite':
        plain_output = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout)
        match = re.search(r'Tests\s+(\d+) passed', plain_output)
        if match:
            step['testCount'] = int(match.group(1))
    report['steps'].append(step)
    if result.stdout:
        print(result.stdout, end='')
    if result.stderr:
        print(result.stderr, end='', file=sys.stderr)
    if result.returncode:
        raise RuntimeError(f'Falló el paso {name!r} (código {result.returncode}).')


def wait_until_ready(process, url, log_path):
    deadline = time.monotonic() + 120
    last_error = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f'El servidor terminó con código {process.returncode}. '
                f'Revisá el registro temporal {log_path}.'
            )
        try:
            with urlopen(url, timeout=2) as response:
                if 200 <= response.status < 400:
                    return
        except (OSError, URLError) as error:
            last_error = error
        time.sleep(0.5)
    raise RuntimeError(
        f'El servidor no respondió en {url}: {last_error}. '
        f'Revisá el registro temporal {log_path}.'
    )


def stop_process(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def drop_e2e_database(database_name):
    connection_options = {
        'dbname': 'postgres',
        'user': os.environ['POSTGRES_USER'],
        'password': os.environ['POSTGRES_PASSWORD'],
        'host': os.getenv('POSTGRES_HOST', '127.0.0.1'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'connect_timeout': 5,
    }
    with psycopg.connect(**connection_options, autocommit=True) as admin_connection:
        admin_connection.execute(
            sql.SQL('DROP DATABASE {} WITH (FORCE)').format(
                sql.Identifier(database_name)
            )
        )


def git_metadata(directory):
    commit = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        cwd=directory,
        capture_output=True,
        text=True,
        check=False,
    )
    status = subprocess.run(
        ['git', 'status', '--porcelain'],
        cwd=directory,
        capture_output=True,
        text=True,
        check=False,
    )
    files = subprocess.run(
        ['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
        cwd=directory, capture_output=True, check=True,
    )
    hashes = {}
    for relative_path in sorted(set(files.stdout.decode('utf-8').split('\0'))):
        path = directory / relative_path
        if relative_path and not relative_path.startswith('reports/') and path.is_file():
            hashes[relative_path] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        'commit': commit.stdout.strip() if commit.returncode == 0 else None,
        'workingTreeDirty': bool(status.stdout.strip()),
        'sourceFileSha256': hashes,
    }


def persist_report(report):
    REPORTS_ROOT.mkdir(exist_ok=True)
    report_path = REPORTS_ROOT / 'TK15-regression-latest.json'
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )
    (REPORTS_ROOT / f"TK15-regression-{report['runId']}.json").write_text(
        report_path.read_text(encoding='utf-8'), encoding='utf-8'
    )
    return report_path


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    development_database, test_database = require_configuration()
    ensure_ports_available()

    report = {
        'task': 'TK15 — Automatizar pruebas y ejecutar regresión',
        'runId': datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
        'startedAt': datetime.now(timezone.utc).isoformat(),
        'environment': {
            'os': sys.platform,
            'python': sys.version.split()[0],
            'django': get_version(),
            'frontendNode': None,
            'frontendNpm': None,
            'database': 'PostgreSQL; isolated transient E2E database',
            'developmentDatabaseModified': False,
            'testDatabase': test_database,
        },
        'revisions': {
            'backend': git_metadata(BACKEND_ROOT),
            'frontend': git_metadata(FRONTEND_ROOT),
        },
        'steps': [],
        'result': 'failed',
    }
    database_name = None
    backend_process = None
    frontend_process = None
    cleanup_error = None

    log_directory = REPORTS_ROOT / report['runId']
    log_directory.mkdir(parents=True, exist_ok=True)
    report['evidenceDirectory'] = str(log_directory.relative_to(BACKEND_ROOT))
    backend_log = log_directory / 'django.log'
    frontend_log = log_directory / 'angular.log'
    try:
        node_version = subprocess.run(
            ['node', '--version'],
            cwd=FRONTEND_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        npm_version = subprocess.run(
            [shutil.which('npm') or 'npm', '--version'],
            cwd=FRONTEND_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        report['environment']['frontendNode'] = node_version.stdout.strip()
        report['environment']['frontendNpm'] = npm_version.stdout.strip()
        lock = json.loads((FRONTEND_ROOT / 'package-lock.json').read_text(encoding='utf-8'))
        report['environment']['playwright'] = lock['packages']['node_modules/@playwright/test']['version']
        report['environment']['angular'] = lock['packages']['node_modules/@angular/core']['version']

        base_environment = environment_for(
            development_database, development_database
        )
        # Never reuse or delete a pre-existing test database.
        base_environment['POSTGRES_TEST_DB'] = f'portfolio_suite_{uuid.uuid4().hex[:12]}'
        report['environment']['testDatabase'] = base_environment['POSTGRES_TEST_DB']
        run_command(
            [
                sys.executable,
                'manage.py',
                'test',
                '--verbosity',
                '1',
                '--noinput',
            ],
            BACKEND_ROOT,
            base_environment,
            report,
            'backend-postgresql-suite',
        )

        database_name = create_e2e_database(
            development_database, test_database
        )
        report['environment']['e2eDatabase'] = database_name
        with psycopg.connect(
            dbname=database_name, user=os.environ['POSTGRES_USER'],
            password=os.environ['POSTGRES_PASSWORD'],
            host=os.getenv('POSTGRES_HOST', '127.0.0.1'),
            port=os.getenv('POSTGRES_PORT', '5432'), connect_timeout=5,
        ) as connection:
            report['environment']['postgresql'] = connection.execute('SHOW server_version').fetchone()[0]
        e2e_environment = environment_for(
            database_name, development_database
        )
        run_command(
            [sys.executable, 'manage.py', 'migrate', '--noinput'],
            BACKEND_ROOT,
            e2e_environment,
            report,
            'create-isolated-e2e-schema',
        )
        run_command(
            [
                sys.executable,
                'manage.py',
                'load_portfolio_e2e_data',
            ],
            BACKEND_ROOT,
            e2e_environment,
            report,
            'load-deterministic-e2e-data',
        )
        run_command(
            ['node', 'node_modules/@angular/cli/bin/ng.js', 'test', '--watch=false'],
            FRONTEND_ROOT, os.environ.copy(), report, 'frontend-unit-suite',
        )
        run_command(
            ['node', 'node_modules/@angular/cli/bin/ng.js', 'build'],
            FRONTEND_ROOT, os.environ.copy(), report, 'frontend-production-build',
        )

        with backend_log.open('w', encoding='utf-8') as output:
            backend_process = subprocess.Popen(
                [
                    sys.executable,
                    'manage.py',
                    'runserver',
                    '--noreload',
                    '127.0.0.1:8000',
                ],
                cwd=BACKEND_ROOT,
                env=e2e_environment,
                stdout=output,
                stderr=subprocess.STDOUT,
            )
        wait_until_ready(backend_process, API_URL + 'perfil/', backend_log)

        with frontend_log.open('w', encoding='utf-8') as output:
            frontend_process = subprocess.Popen(
                [
                    'node',
                    'node_modules/@angular/cli/bin/ng.js',
                    'serve',
                    '--host',
                    '127.0.0.1',
                    '--port',
                    str(FRONTEND_PORT),
                ],
                cwd=FRONTEND_ROOT,
                env=os.environ.copy(),
                stdout=output,
                stderr=subprocess.STDOUT,
            )
        wait_until_ready(frontend_process, FRONTEND_URL, frontend_log)

        playwright_cli = FRONTEND_ROOT / 'node_modules' / 'playwright' / 'cli.js'
        browser_environment = os.environ.copy()
        browser_environment.update(
            {
                'PLAYWRIGHT_BASE_URL': FRONTEND_URL.rstrip('/'),
                'PORTFOLIO_API_BASE_URL': API_URL.rstrip('/'),
                'PORTFOLIO_REAL_API': '1',
                'PLAYWRIGHT_HTML_OUTPUT_DIR': str(log_directory / 'playwright-report'),
                'PLAYWRIGHT_JSON_OUTPUT_FILE': str(log_directory / 'playwright-results.json'),
            }
        )
        run_command(
            ['node', str(playwright_cli), 'test', '--workers=2',
             '--output', str(log_directory / 'test-results')],
            FRONTEND_ROOT,
            browser_environment,
            report,
            'frontend-playwright-regression',
        )
        run_command(
            [sys.executable, 'scripts/probe_integrated.py'],
            BACKEND_ROOT,
            browser_environment,
            report,
            'frontend-backend-http-integration-probe',
        )
        report['result'] = 'passed'
    except Exception as error:
        report['failure'] = str(error)
        raise
    finally:
        stop_process(frontend_process)
        stop_process(backend_process)
        playwright_results = log_directory / 'playwright-results.json'
        if playwright_results.exists():
            report['playwrightStats'] = json.loads(playwright_results.read_text(encoding='utf-8'))['stats']
        if database_name is not None:
            try:
                drop_e2e_database(database_name)
                report['environment']['e2eDatabaseCleanedUp'] = True
            except Exception as error:
                report['result'] = 'failed'
                report['environment']['e2eDatabaseCleanedUp'] = False
                cleanup_error = error
                report['cleanupFailure'] = str(error)
        report['testCases'] = {'BE-CP22': report['result']}
        report['finishedAt'] = datetime.now(timezone.utc).isoformat()
        report_path = persist_report(report)
        print(f'Informe de regresión: {report_path}')
        if cleanup_error is not None:
            raise RuntimeError(
                'No se pudo eliminar la base E2E temporal; revisá el informe '
                'de regresión y eliminá únicamente esa base cuando confirmes '
                'que el servidor terminó.'
            ) from cleanup_error

    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f'Error de regresión: {error}', file=sys.stderr)
        raise
