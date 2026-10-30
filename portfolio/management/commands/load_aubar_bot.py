"""Add the owner's ESP32 project without overwriting existing portfolio data."""
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models import Max

from portfolio.models import Proyecto, Tecnologia

PROJECT = {
    'title': 'Aubar Bot',
    'slug': 'aubar-bot',
    'summary': 'Asistente de escritorio con ESP32, avatar animado, control por voz e inteligencia artificial.',
    'description': (
        'Asistente de escritorio con ESP32-S3, avatar animado y control por voz. '
        'Desarrollado en C++ y Python, integra conversaciones con IA mediante Groq, '
        'respuestas habladas con Dora y reproducción de videos de YouTube.'
    ),
    'project_type': 'Proyecto personal · Hardware e IA',
    'image_url': 'https://raw.githubusercontent.com/aubarcito48/aubar-bot/e8454ea277a1cf00a5168490accfc7d2c6310462/docs/images/kirby-ojos-semicerrados-ilustracion.png',
    'image_alt': 'Avatar de Aubar Bot en una pantalla Waveshare ESP32-S3',
    'demo_url': '',
    'demo_label': 'Ver demo',
    'repository_url': 'https://github.com/aubarcito48/aubar-bot',
    'repository_label': 'Repositorio',
    'order': 3,
}

NEW_TECHNOLOGIES = {
    'C++': 'https://isocpp.org/',
    'Arduino': 'https://docs.arduino.cc/',
    'ESP32': 'https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/index.html',
}
TECHNOLOGIES = ('Python', 'C++', 'Arduino', 'ESP32')


def load_project(publish=False):
    """Caller owns the transaction and selects the explicit target schema."""
    technologies = []
    next_order = (Tecnologia.objects.aggregate(last=Max('order'))['last'] or 0) + 1
    for name in TECHNOLOGIES:
        matches = list(Tecnologia.objects.filter(name=name))
        if len(matches) > 1:
            raise CommandError(f'Ambiguous technology: {name}. No changes committed.')
        if matches:
            technology = matches[0]
            if not technology.is_published:
                raise CommandError(f'Technology is unpublished: {name}. Refusing to change it.')
        elif name in NEW_TECHNOLOGIES:
            technology = Tecnologia(name=name, category='Sistemas embebidos',
                url=NEW_TECHNOLOGIES[name], order=next_order, is_published=True)
            technology.save()
            next_order += 1
        else:
            raise CommandError(f'Required published technology missing: {name}.')
        technologies.append(technology)
    project = Proyecto.objects.filter(slug=PROJECT['slug']).first()
    created = project is None
    if project is None:
        if Proyecto.objects.filter(repository_url=PROJECT['repository_url']).exists():
            raise CommandError('Repository already belongs to another project.')
        project = Proyecto(**PROJECT, is_published=publish)
        project.save()
        project.technologies.set(technologies)
    else:
        if any(getattr(project, key) != value for key, value in PROJECT.items()):
            raise CommandError('Existing project differs; refusing to overwrite it.')
        if set(project.technologies.values_list('pk', flat=True)) != {t.pk for t in technologies}:
            raise CommandError('Existing project technologies differ; no changes committed.')
        if project.additional_links.exists():
            raise CommandError('Existing project links differ; no changes committed.')
        if publish and not project.is_published:
            project.is_published = True
            project.save(update_fields=['is_published'])
    return project, created


class Command(BaseCommand):
    help = 'Add Aubar Bot and its missing embedded-system technologies, with schema and conflict guards.'

    def add_arguments(self, parser):
        parser.add_argument('--schema', choices=('public', 'portfolio_django'), required=True)
        parser.add_argument('--publish', action='store_true')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        if connection.vendor != 'postgresql':
            raise CommandError('This command requires PostgreSQL.')
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(f'SET LOCAL search_path TO "{options["schema"]}", pg_catalog')
                cursor.execute("SET LOCAL lock_timeout = '5s'")
                cursor.execute("SET LOCAL statement_timeout = '15s'")
                cursor.execute('LOCK TABLE portfolio_proyecto, portfolio_tecnologia, '
                               'portfolio_proyecto_technologies IN SHARE ROW EXCLUSIVE MODE')
            project, created = load_project(options['publish'])
            if options['dry_run']:
                transaction.set_rollback(True)
            self.stdout.write(f'Aubar Bot: id={project.pk}; schema={options["schema"]}; '
                f'created={created}; published={project.is_published}; dry_run={options["dry_run"]}.')
