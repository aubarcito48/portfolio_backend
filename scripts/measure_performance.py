"""TK16: real local HTTP measurements on a newly created PostgreSQL database."""
import argparse
import hashlib
import json
import math
import os
import platform
import socket
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

import psycopg

from run_regression import (
    BACKEND_ROOT, REPORTS_ROOT, create_e2e_database, drop_e2e_database,
    environment_for, git_metadata, require_configuration, run_command, stop_process,
)

ENDPOINTS = (
    '/api/v1/perfil/', '/api/v1/tecnologias/', '/api/v1/experiencias/',
    '/api/v1/formacion/', '/api/v1/enlaces/', '/api/v1/proyectos/',
    '/api/v1/proyectos/?page_size=100', '/api/v1/proyectos/tk16-project-001/',
)
ORIGIN = 'http://127.0.0.1:8765'


def percentile95(values):
    return sorted(values)[math.ceil(len(values) * 0.95) - 1]


def request_sample(endpoint):
    started = time.perf_counter_ns()
    status, body, error = None, b'', None
    try:
        with urlopen(ORIGIN + endpoint, timeout=10) as response:
            body, status = response.read(), response.status
    except HTTPError as exc:
        status, body, error = exc.code, exc.read(), f'HTTP {exc.code}'
    except OSError as exc:
        error = str(exc)
    elapsed = (time.perf_counter_ns() - started) / 1_000_000
    return {'elapsedMs': round(elapsed, 4), 'status': status, 'error': error,
            'bytes': len(body), 'bodySha256': hashlib.sha256(body).hexdigest()}


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True, choices=('before', 'after'))
    parser.add_argument('--compare', type=Path)
    parser.add_argument('--run-tests', action='store_true',
                        help='Run Django regression after all measurements, in another temporary DB.')
    args = parser.parse_args()
    development, test = require_configuration()
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 8765))
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    folder = REPORTS_ROOT / f'TK16-{run_id}-{args.label}'
    folder.mkdir(parents=True)
    report_path = REPORTS_ROOT / f'TK16-{run_id}-{args.label}.json'
    report = {
        'task': 'TK16', 'case': 'BE-CP23', 'label': args.label, 'runId': run_id,
        'startedAt': datetime.now(timezone.utc).isoformat(), 'result': 'failed',
        'revision': git_metadata(BACKEND_ROOT), 'steps': [],
        'environment': {'platform': platform.platform(), 'python': platform.python_version(),
                        'logicalCpuCount': os.cpu_count(), 'debug': False,
                        'server': 'Django runserver --noreload --nothreading',
                        'origin': ORIGIN, 'concurrency': 1, 'httpKeepAlive': False,
                        'warmupsPerEndpoint': 5, 'samplesPerEndpoint': 50,
                        'p95Method': 'nearest rank: sorted[ceil(0.95*n)-1]',
                        'thresholdMs': 1000, 'sqlInstrumentationDuringHttp': False},
        'dataset': {'version': 1, 'publishedProjects': 100, 'draftProjects': 1,
                    'technologies': 12, 'technologiesPerProject': 6,
                    'publishedTechnologiesPerProject': 5, 'additionalLinksPerProject': 2},
        'evidenceDirectory': str(folder.relative_to(BACKEND_ROOT)),
    }
    database, process = None, None
    try:
        database = create_e2e_database(development, test)
        report['environment']['temporaryDatabase'] = database
        env = environment_for(database, development)
        env['DJANGO_CORS_ALLOWED_ORIGINS'] = ''
        with psycopg.connect(dbname=database, user=env['POSTGRES_USER'],
                             password=env['POSTGRES_PASSWORD'],
                             host=env.get('POSTGRES_HOST', '127.0.0.1'),
                             port=env.get('POSTGRES_PORT', '5432')) as connection:
            report['environment']['postgresql'] = connection.execute('SHOW server_version').fetchone()[0]
        import django
        report['environment']['django'] = django.get_version()
        for name, command in (
            ('migrate', ['migrate', '--noinput']),
            ('deterministic-fixture', ['load_portfolio_performance_data']),
        ):
            run_command([sys.executable, 'manage.py', *command], BACKEND_ROOT, env, report, name)
        # TCP readiness doesn't invoke any API. First HTTP request stays cold.
        started = time.perf_counter_ns()
        with (folder / 'django.log').open('w', encoding='utf-8') as output:
            process = subprocess.Popen(
                [sys.executable, 'manage.py', 'runserver', '--noreload', '--nothreading', '127.0.0.1:8765'],
                cwd=BACKEND_ROOT, env=env, stdout=output, stderr=subprocess.STDOUT,
            )
        deadline = time.monotonic() + 60
        while True:
            if process.poll() is not None:
                raise RuntimeError('Django stopped before readiness; inspect django.log.')
            try:
                with socket.create_connection(('127.0.0.1', 8765), timeout=0.2):
                    break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError('Django startup timeout.')
                time.sleep(0.025)
        cold = request_sample(ENDPOINTS[0])
        cold['processStartToFirstResponseMs'] = round((time.perf_counter_ns() - started) / 1_000_000, 4)
        cold['endpoint'] = ENDPOINTS[0]
        report['coldStart'] = cold
        report['endpoints'] = []
        for endpoint in ENDPOINTS:
            warmups = [request_sample(endpoint) for _ in range(5)]
            samples = [request_sample(endpoint) for _ in range(50)]
            times = [sample['elapsedMs'] for sample in samples]
            errors = sum(s['status'] != 200 or s['error'] is not None for s in samples)
            report['endpoints'].append({
                'endpoint': endpoint, 'samples': samples, 'warmups': warmups,
                'p95Ms': percentile95(times), 'minMs': min(times), 'maxMs': max(times),
                'meanMs': round(sum(times) / len(times), 4), 'errors': errors,
                'withinTarget': percentile95(times) <= 1000,
                'stableContent': len({s['bodySha256'] for s in samples}) == 1,
            })
            print(f'{endpoint}: p95={percentile95(times):.3f} ms, errors={errors}', flush=True)
        run_command(
            [sys.executable, 'manage.py', 'profile_api_queries', '--output', str(folder / 'queries.json')],
            BACKEND_ROOT, env, report, 'query-profile',
        )
        report['queries'] = json.loads((folder / 'queries.json').read_text(encoding='utf-8'))
        if args.compare:
            before = json.loads(args.compare.read_text(encoding='utf-8'))
            ignored = {'temporaryDatabase', 'databaseCleanedUp'}
            before_conditions = {k: v for k, v in before['environment'].items() if k not in ignored}
            after_conditions = {k: v for k, v in report['environment'].items() if k not in ignored}
            if before['dataset'] != report['dataset'] or before_conditions != after_conditions:
                raise RuntimeError('Comparison requires identical dataset and measurement conditions.')
            report['comparison'] = {
                'baseline': str(args.compare), 'endpoints': [
                    {'endpoint': a['endpoint'], 'beforeP95Ms': b['p95Ms'], 'afterP95Ms': a['p95Ms'],
                     'deltaP95Ms': round(a['p95Ms'] - b['p95Ms'], 4),
                     'sameContent': a['samples'][0]['bodySha256'] == b['samples'][0]['bodySha256'],
                     'beforeQueries': before['queries'][i]['samples'][0]['count'],
                     'afterQueries': report['queries'][i]['samples'][0]['count']}
                    for i, (b, a) in enumerate(zip(before['endpoints'], report['endpoints'], strict=True))
                ],
            }
        passed = (cold['status'] == 200 and all(
            e['errors'] == 0 and e['withinTarget'] and e['stableContent']
            and all(w['status'] == 200 for w in e['warmups']) for e in report['endpoints']
        ) and all(s['status'] == 200 for q in report['queries'] for s in q['samples']))
        if args.compare:
            passed = passed and all(e['sameContent'] for e in report['comparison']['endpoints'])
        report['result'] = 'passed' if passed else 'failed'
        if args.run_tests:
            test_env = env.copy()
            test_env['POSTGRES_TEST_DB'] = f'portfolio_suite_{uuid.uuid4().hex[:12]}'
            report['validationTestDatabase'] = test_env['POSTGRES_TEST_DB']
            run_command(
                [sys.executable, 'manage.py', 'test', '--noinput'],
                BACKEND_ROOT, test_env, report, 'backend-regression-after-measurement',
            )
    except Exception as error:
        report['failure'] = str(error)
        raise
    finally:
        stop_process(process)
        if database:
            try:
                drop_e2e_database(database)
                report['environment']['databaseCleanedUp'] = True
            except Exception as error:
                report['result'] = 'failed'
                report['cleanupFailure'] = str(error)
        report['finishedAt'] = datetime.now(timezone.utc).isoformat()
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'Report: {report_path}')
    return 0 if report['result'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
