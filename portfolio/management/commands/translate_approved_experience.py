"""Translate only the exact previously approved work history; preserve its identity."""
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from portfolio.models import Experiencia
from .load_approved_experience import APPROVED_EXPERIENCE, ORIGINAL_EXPERIENCE


class Command(BaseCommand):
    help = 'Translate approved experience to Spanish without replacing unrelated edits.'

    def handle(self, *args, **options):
        if connection.vendor != 'postgresql':
            raise CommandError('This command requires PostgreSQL.')
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('SET LOCAL lock_timeout = \'5s\'')
                cursor.execute('LOCK TABLE portfolio_experiencia IN SHARE ROW EXCLUSIVE MODE')
            existing = list(Experiencia.objects.all())
            if len(existing) != len(APPROVED_EXPERIENCE):
                raise CommandError('Unexpected experience count; no data changed.')
            prepared = []
            for original, translated in zip(ORIGINAL_EXPERIENCE, APPROVED_EXPERIENCE):
                matches = [item for item in existing
                           if item.organization == original['organization']]
                if len(matches) != 1:
                    raise CommandError('Missing or duplicate experience; no data changed.')
                item = matches[0]
                if not any(all(getattr(item, key) == value for key, value in version.items())
                           for version in (original, translated)):
                    raise CommandError('Experience was edited; refusing to overwrite it.')
                item.title = translated['title']
                item.description = translated['description']
                item.full_clean()
                prepared.append(item)
            for item in prepared:
                item.save(update_fields=['title', 'description'])
        self.stdout.write('Spanish experience verified: 3 records; identities and publication preserved.')
