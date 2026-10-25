"""Publish the weather project supplied by the portfolio owner on 2026-10-25."""
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from portfolio.models import EnlaceProyecto, Proyecto, Tecnologia


PROJECT = {
    'title': 'StitchWeather',
    'slug': 'stitchweather',
    'summary': 'Aplicación del clima con pronóstico, geolocalización y recomendaciones con inteligencia artificial.',
    'description': (
        'Aplicación del clima con búsqueda de ciudades, geolocalización y pronóstico. '
        'Integra OpenWeather y recomendaciones con IA mediante Groq, con interfaz '
        'en español e inglés. Desarrollada con Angular, Tailwind CSS, Python y Django.'
    ),
    'project_type': 'Proyecto personal',
    'image_url': 'https://app-clima-ecru.vercel.app/app-clima.png',
    'image_alt': 'StitchWeather con el clima de Córdoba y recomendaciones generadas con inteligencia artificial',
    'demo_url': 'https://app-clima-ecru.vercel.app/',
    'demo_label': 'Ver demo',
    'repository_url': 'https://github.com/aubarcito48/app-clima-backend',
    'repository_label': 'Backend',
    'order': 2,
}
TECHNOLOGIES = ('Angular', 'Tailwind CSS', 'Python', 'Django', 'REST APIs')
FRONTEND = 'https://github.com/aubarcito48/app-clima'


class Command(BaseCommand):
    help = 'Load StitchWeather without changing existing projects or technologies.'

    def add_arguments(self, parser):
        parser.add_argument('--schema', choices=('public', 'portfolio_django'), required=True)
        parser.add_argument('--publish', action='store_true')

    def handle(self, *args, **options):
        if connection.vendor != 'postgresql':
            raise CommandError('This command requires PostgreSQL.')
        with transaction.atomic():
            with connection.cursor() as cursor:
                # Fixed allowlist above; never interpolate an arbitrary identifier.
                cursor.execute(f'SET LOCAL search_path TO "{options["schema"]}", pg_catalog')
                cursor.execute("SET LOCAL lock_timeout = '5s'")
                cursor.execute(
                    'LOCK TABLE portfolio_proyecto, portfolio_enlaceproyecto, '
                    'portfolio_proyecto_technologies IN SHARE ROW EXCLUSIVE MODE'
                )
            technologies = []
            for name in TECHNOLOGIES:
                matches = list(Tecnologia.objects.filter(name=name, is_published=True))
                if len(matches) != 1:
                    raise CommandError(f'Expected one published technology: {name}.')
                technologies.append(matches[0])
            project = Proyecto.objects.filter(slug=PROJECT['slug']).first()
            created = project is None
            if project is None:
                if Proyecto.objects.filter(repository_url=PROJECT['repository_url']).exists():
                    raise CommandError('Backend repository is already assigned to a project.')
                if EnlaceProyecto.objects.filter(url=FRONTEND).exists():
                    raise CommandError('Frontend repository is already assigned to a project.')
                project = Proyecto(**PROJECT, is_published=options['publish'])
                project.save()
                project.technologies.set(technologies)
                EnlaceProyecto.objects.create(project=project, label='Frontend', url=FRONTEND, order=0)
            else:
                if any(getattr(project, key) != value for key, value in PROJECT.items()):
                    raise CommandError('Existing project was edited; refusing to overwrite it.')
                if set(project.technologies.values_list('id', flat=True)) != {t.pk for t in technologies}:
                    raise CommandError('Existing technologies differ; no changes made.')
                if list(project.additional_links.values_list('label', 'url', 'order')) != [('Frontend', FRONTEND, 0)]:
                    raise CommandError('Existing links differ; no changes made.')
                if options['publish'] and not project.is_published:
                    project.is_published = True
                    project.save(update_fields=['is_published'])
            self.stdout.write(
                f'StitchWeather: id={project.pk}; schema={options["schema"]}; '
                f'created={created}; published={project.is_published}.'
            )
