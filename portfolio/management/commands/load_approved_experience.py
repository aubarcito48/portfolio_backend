"""Load the work history explicitly supplied and approved by the owner."""
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from portfolio.models import Experiencia


# Dates represent month precision; the owner confirmed January for freelance.
# Preserve the titles, tasks and ordering supplied by the owner.
APPROVED_EXPERIENCE = (
    {
        'title': 'Web Development Intern',
        'organization': 'DGES',
        'description': (
            'Worked with WordPress in a professional environment.\n'
            'Gained practical experience in website development and maintenance.'
        ),
        'start_date': date(2025, 6, 1), 'end_date': date(2025, 11, 1),
        'is_current': False, 'order': 0,
    },
    {
        'title': 'Freelance Full-Stack Developer',
        'organization': 'Freelance',
        'description': (
            'Develop web applications and work on frontend and backend functionality.\n'
            'Integrate APIs and work with databases.\n'
            'Use version control and collaborative development tools.'
        ),
        'start_date': date(2023, 1, 1), 'end_date': None,
        'is_current': True, 'order': 1,
    },
    {
        'title': 'IT Technical Support',
        'organization': 'Sanatorio Francés',
        'description': (
            'Provided technical support in an organizational environment.\n'
            'Assisted with troubleshooting and resolving IT-related issues.'
        ),
        'start_date': date(2024, 11, 1), 'end_date': date(2025, 5, 1),
        'is_current': False, 'order': 2,
    },
)


class Command(BaseCommand):
    help = 'Create approved work history without overwriting existing content.'

    def add_arguments(self, parser):
        parser.add_argument('--publish', action='store_true', help='Publish approved experience.')

    def handle(self, *args, **options):
        if connection.vendor != 'postgresql':
            raise CommandError('This command requires PostgreSQL.')
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('LOCK TABLE portfolio_experiencia IN SHARE ROW EXCLUSIVE MODE')
            existing = list(Experiencia.objects.all())
            keys = {(item['title'], item['organization']) for item in APPROVED_EXPERIENCE}
            if any((item.title, item.organization) not in keys for item in existing):
                raise CommandError('Other experience exists; review it before loading. No data changed.')
            prepared = []
            for data in APPROVED_EXPERIENCE:
                matches = [item for item in existing
                           if (item.title, item.organization) == (data['title'], data['organization'])]
                if len(matches) > 1:
                    raise CommandError('Duplicate experience exists; no data changed.')
                item = matches[0] if matches else Experiencia(**data, is_published=False)
                if matches and any(getattr(item, key) != value for key, value in data.items()):
                    raise CommandError('Existing experience differs; refusing to overwrite it.')
                item.is_published = item.is_published or options['publish']
                item.full_clean()
                prepared.append(item)
            for item in prepared:
                item.save()
        self.stdout.write(f'Approved experience verified: {len(prepared)} records; '
                          f'published: {sum(item.is_published for item in prepared)}.')
