"""Publish the owner's CV through the existing professional-link model."""
from datetime import datetime, timezone
import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models import Max, Q

from portfolio.models import Enlace

CV = {
    'label': 'Curriculum Vitae',
    'type': 'cv',
    'url': 'https://drive.google.com/file/d/1Oy3AnWPr2F6JOtoWTRjgQh4jsKfWaBNm/view?usp=sharing',
}
CV_EN = {
    'label': 'Curriculum Vitae (English)',
    'type': 'cv_en',
    'url': 'https://drive.google.com/file/d/1KtHtqDxkDJo-1u0IvB1__EvKIzHVTvMY/view?usp=sharing',
}


def load_cv(language='es'):
    cv = {'es': CV, 'en': CV_EN}[language]
    matches = list(Enlace.objects.filter(Q(type=cv['type']) | Q(url=cv['url'])))
    if len(matches) > 1:
        raise CommandError('Multiple CV links found; refusing to alter them.')
    if matches:
        link = matches[0]
        if any(getattr(link, key) != value for key, value in cv.items()) or not link.is_published:
            raise CommandError('Existing CV differs; refusing to overwrite it.')
        return link, False
    link = Enlace(**cv, order=(Enlace.objects.aggregate(last=Max('order'))['last'] or 0) + 1,
                  is_published=True)
    link.save()
    return link, True


class Command(BaseCommand):
    help = 'Add the published CV link without changing existing links or database structure.'

    def add_arguments(self, parser):
        parser.add_argument('--schema', choices=('public', 'portfolio_django'), required=True)
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--language', choices=('es', 'en'), default='es')

    def handle(self, *args, **options):
        if connection.vendor != 'postgresql':
            raise CommandError('This guarded publication command requires PostgreSQL.')
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(f'SET LOCAL search_path TO "{options["schema"]}", pg_catalog')
                cursor.execute("SET LOCAL lock_timeout='5s'")
                cursor.execute("SET LOCAL statement_timeout='10s'")
                cursor.execute('LOCK TABLE portfolio_enlace IN SHARE ROW EXCLUSIVE MODE')
            before = list(Enlace.objects.values())
            backup_dir = settings.BASE_DIR / 'backups'
            backup_dir.mkdir(exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            backup = backup_dir / f'cv-link-{stamp}-{options["schema"]}.json'
            backup.write_text(json.dumps(before, ensure_ascii=False, indent=2), encoding='utf-8')
            link, created = load_cv(options['language'])
            expected = list(Enlace.objects.values()) if not created else [row for row in Enlace.objects.values() if row['id'] != link.pk]
            if before != expected:
                raise CommandError('Existing links changed; rolling back.')
            first = list(Enlace.objects.values())
            repeated, second_created = load_cv(options['language'])
            if second_created or repeated.pk != link.pk or list(Enlace.objects.values()) != first:
                raise CommandError('Repeated load changed data; rolling back.')
            if options['dry_run']:
                transaction.set_rollback(True)
            self.stdout.write(json.dumps({'cvId': link.pk, 'schema': options['schema'],
                'created': created, 'dryRun': options['dry_run'], 'existingLinksUnchanged': True,
                'backup': str(backup.relative_to(settings.BASE_DIR))}))
