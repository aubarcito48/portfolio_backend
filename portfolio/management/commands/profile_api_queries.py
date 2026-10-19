import json
from pathlib import Path

from django.core.management import BaseCommand
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext


ENDPOINTS = (
    '/api/v1/perfil/', '/api/v1/tecnologias/', '/api/v1/experiencias/',
    '/api/v1/formacion/', '/api/v1/enlaces/', '/api/v1/proyectos/',
    '/api/v1/proyectos/?page_size=100', '/api/v1/proyectos/tk16-project-001/',
)


class Command(BaseCommand):
    help = 'Captura SQL de los endpoints sin instrumentar las mediciones HTTP.'

    def add_arguments(self, parser):
        parser.add_argument('--output', required=True)

    def handle(self, *args, **options):
        client = Client(HTTP_HOST='127.0.0.1')
        connection.ensure_connection()
        results = []
        for endpoint in ENDPOINTS:
            samples = []
            for _ in range(3):
                with CaptureQueriesContext(connection) as queries:
                    response = client.get(endpoint)
                samples.append({
                    'status': response.status_code, 'count': len(queries),
                    'queries': list(queries.captured_queries),
                })
            results.append({'endpoint': endpoint, 'samples': samples})
        Path(options['output']).write_text(
            json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8',
        )
        self.stdout.write('SQL capturado: 3 peticiones por endpoint, conexión inicializada.')
