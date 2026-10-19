import os
from datetime import date

from django.conf import settings
from django.core.management import BaseCommand
from django.db import connection, transaction

from portfolio.management.commands.load_portfolio_e2e_data import validate_e2e_database
from portfolio.models import Enlace, EnlaceProyecto, Experiencia, Formacion, Perfil, Proyecto, Tecnologia


class Command(BaseCommand):
    help = 'TK16: recrea datos sintéticos exclusivamente en una base E2E descartable.'

    def handle(self, *args, **options):
        validate_e2e_database(
            settings.ENVIRONMENT, connection.settings_dict['NAME'],
            os.getenv('PORTFOLIO_E2E_DATABASE'),
            os.getenv('PORTFOLIO_DEVELOPMENT_DATABASE'),
            settings.DATABASES['default']['TEST']['NAME'],
        )
        with transaction.atomic():
            for model in (Proyecto, Tecnologia, Experiencia, Formacion, Enlace, Perfil):
                model.objects.all().delete()
            Perfil.objects.create(
                pk=1, name='TK16 Profile', professional_title='Synthetic benchmark',
                biography='Deterministic performance fixture.', location='Local test',
                image_url='/assets/nahuel.jpg', is_published=True,
            )
            technologies = [Tecnologia.objects.create(
                pk=i, name=f'TK16 Technology {i:02}', category=f'Category {i % 3}',
                url=f'https://example.test/technology/{i}', order=i // 2,
                is_published=i <= 10,
            ) for i in range(1, 13)]
            for i in range(1, 102):
                project = Proyecto.objects.create(
                    pk=i, title=f'TK16 Project {i:03}', slug=f'tk16-project-{i:03}',
                    summary=f'Synthetic summary {i:03}',
                    description=('Deterministic project description. ' * 12).strip(),
                    project_type='Benchmark', order=i // 2, is_published=i <= 100,
                    repository_url=f'https://example.test/repository/{i}',
                )
                project.technologies.set([
                    technologies[(i + offset) % 10] for offset in range(5)
                ] + [technologies[10]])
                for j in range(2):
                    EnlaceProyecto.objects.create(
                        pk=(i - 1) * 2 + j + 1, project=project,
                        label=f'Link {j}', url=f'https://example.test/project/{i}/{j}', order=j,
                    )
            for i in range(1, 12):
                Experiencia.objects.create(
                    pk=i, title=f'TK16 Experience {i:02}', organization='Synthetic',
                    description='Benchmark fixture', start_date=date(2025, 1, 1),
                    is_current=True, order=i // 2, is_published=i <= 10,
                )
                Formacion.objects.create(
                    pk=i, name=f'TK16 Education {i:02}', institution='Synthetic',
                    type=Formacion.Type.STUDY, status=Formacion.Status.IN_PROGRESS,
                    start_date=date(2025, 1, 1), order=i // 2, is_published=i <= 10,
                )
                Enlace.objects.create(
                    pk=i, label=f'TK16 Link {i:02}', type='benchmark',
                    url=f'https://example.test/link/{i}', order=i // 2, is_published=i <= 10,
                )
        self.stdout.write('TK16: 100 proyectos publicados + 1 borrador, 12 tecnologías, '
                          '606 relaciones y 202 enlaces de proyecto. Datos sintéticos.')
