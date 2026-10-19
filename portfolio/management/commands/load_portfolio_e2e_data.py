import os
from datetime import date

from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command
from django.db import connection, transaction

from portfolio.models import Enlace, Experiencia, Formacion, Proyecto, Tecnologia


def validate_e2e_database(environment, database_name, e2e_database,
                          development_database, test_database):
    if (
        environment != 'test'
        or not e2e_database
        or database_name != e2e_database
        or not development_database
        or database_name == development_database
        or database_name == test_database
        or not database_name.startswith('portfolio_e2e_')
    ):
        raise CommandError(
            'La carga E2E requiere un nombre de base explícito y distinto '
            'de las bases de desarrollo y pruebas.'
        )


class Command(BaseCommand):
    help = 'Prepara datos públicos y borradores para la regresión E2E local.'

    def handle(self, *args, **options):
        database_name = connection.settings_dict['NAME']
        e2e_database = os.environ.get('PORTFOLIO_E2E_DATABASE')
        development_database = os.environ.get('PORTFOLIO_DEVELOPMENT_DATABASE')
        test_database = settings.DATABASES['default']['TEST']['NAME']

        validate_e2e_database(settings.ENVIRONMENT, database_name, e2e_database,
                              development_database, test_database)

        with transaction.atomic():
            call_command('load_portfolio_data', stdout=self.stdout)
            draft_technology, _ = Tecnologia.objects.update_or_create(
                name='TK15 Draft Technology',
                category='TK15 Test Data',
                defaults={
                    'url': 'https://example.test/draft-technology',
                    'order': 999,
                    'is_published': False,
                },
            )
            draft_project, _ = Proyecto.objects.update_or_create(
                slug='tk15-draft-project',
                defaults={
                    'title': 'TK15 Draft Project',
                    'summary': 'Unpublished test project.',
                    'description': 'This record must never appear in public output.',
                    'project_type': 'E2E fixture',
                    'order': 999,
                    'is_published': False,
                },
            )
            draft_project.technologies.set([draft_technology])
            Proyecto.objects.get(slug='pintaebook').technologies.add(draft_technology)
            Enlace.objects.update_or_create(
                type='tk15-draft',
                defaults={
                    'label': 'TK15 Draft Link',
                    'url': 'https://example.test/draft-link',
                    'order': 999,
                    'is_published': False,
                },
            )
            for published in (True, False):
                marker = 'Published' if published else 'Draft'
                Experiencia.objects.update_or_create(
                    title=f'TK15 {marker} Experience',
                    organization='TK15 deterministic fixture',
                    defaults={
                        'description': 'Synthetic regression data, not professional history.',
                        'start_date': date(2025, 1, 1),
                        'is_current': True,
                        'is_published': published,
                    },
                )
                Formacion.objects.update_or_create(
                    name=f'TK15 {marker} Education',
                    institution='TK15 deterministic fixture',
                    defaults={
                        'type': Formacion.Type.STUDY,
                        'status': Formacion.Status.IN_PROGRESS,
                        'start_date': date(2025, 1, 1),
                        'is_published': published,
                    },
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Los datos de regresión se cargaron en la base E2E {database_name!r}.'
            )
        )
