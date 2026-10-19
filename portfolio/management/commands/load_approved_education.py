"""Load only the education explicitly approved by the portfolio owner."""
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from portfolio.models import Formacion


APPROVED_EDUCATION = (
    {
        'name': 'Tecnicatura Superior en Desarrollo de Software',
        'institution': 'Instituto Superior Politécnico de Córdoba',
        'type': 'study', 'status': 'in_progress',
        # Owner confirmed March 2024 for ISPC; day 1 represents month precision.
        'start_date': date(2024, 3, 1), 'end_date': None, 'url': '', 'order': 0,
    },
    {
        'name': 'Junior Full Stack Developer',
        'institution': 'Instituto Superior Politécnico de Córdoba (ISPC)',
        'type': 'certification', 'status': 'completed',
        'start_date': date(2024, 3, 1), 'end_date': date(2026, 6, 1),
        'url': 'https://drive.google.com/file/d/15w_zreSg-nibw8ym0zN_hmLlS25GfQP6/view?usp=sharing',
        'order': 1,
    },
)


class Command(BaseCommand):
    help = 'Create owner-approved ISPC education without overwriting existing content.'

    def add_arguments(self, parser):
        parser.add_argument('--publish', action='store_true',
                            help='Publish the approved study and intermediate certificate.')

    def handle(self, *args, **options):
        if connection.vendor != 'postgresql':
            raise CommandError('This command requires PostgreSQL.')
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('LOCK TABLE portfolio_formacion IN SHARE ROW EXCLUSIVE MODE')
            existing = list(Formacion.objects.all())
            approved_names = {item['name'] for item in APPROVED_EDUCATION}
            if any(item.name not in approved_names for item in existing):
                raise CommandError('Other education exists; review it before loading. No data changed.')
            prepared = []
            for data in APPROVED_EDUCATION:
                matches = [item for item in existing if item.name == data['name']]
                if len(matches) > 1:
                    raise CommandError('Duplicate education exists; no data changed.')
                item = matches[0] if matches else Formacion(**data, is_published=False)
                if matches and any(getattr(item, key) != value for key, value in data.items()):
                    raise CommandError('Existing education differs; refusing to overwrite it.')
                item.is_published = item.is_published or options['publish']
                item.full_clean()
                prepared.append(item)
            for item in prepared:
                item.save()
        self.stdout.write(f'Approved education verified: {len(prepared)} records; '
                          f'published: {sum(item.is_published for item in prepared)}. Owner-approved ISPC dates.')
