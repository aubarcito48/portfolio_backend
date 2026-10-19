from io import StringIO

from django.core.management import call_command, CommandError
from django.test import TestCase

from portfolio.models import Formacion


class ApprovedEducationTests(TestCase):
    def load(self, **options):
        call_command('load_approved_education', stdout=StringIO(), **options)

    def test_public_education_uses_approved_ispc_dates_and_drive_link(self):
        self.load(publish=True)
        response = self.client.get('/api/v1/formacion/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 2)
        self.assertTrue(all(item['startDate'] == '2024-03-01' for item in response.json()['results']))
        self.assertEqual(response.json()['results'][1]['endDate'], '2026-06-01')
        self.assertIn('drive.google.com', response.json()['results'][1]['url'])

    def test_default_is_draft_then_publish_is_idempotent_and_keeps_ids(self):
        self.load()
        ids = list(Formacion.objects.values_list('pk', flat=True))
        self.assertEqual(self.client.get('/api/v1/formacion/').json()['count'], 0)
        self.load(publish=True)
        self.load(publish=True)
        self.assertEqual(list(Formacion.objects.values_list('pk', flat=True)), ids)
        self.assertEqual(Formacion.objects.filter(is_published=True).count(), 2)

    def test_existing_edits_are_preserved_and_loading_is_atomic(self):
        self.load()
        Formacion.objects.filter(type='certification').update(institution='Owner edit')
        with self.assertRaises(CommandError):
            self.load(publish=True)
        self.assertEqual(Formacion.objects.filter(is_published=True).count(), 0)
        self.assertEqual(Formacion.objects.get(type='certification').institution, 'Owner edit')

    def test_unrelated_education_is_not_overwritten(self):
        Formacion.objects.create(name='Other study', institution='Other institution',
                                 type='study', status='in_progress', start_date='2024-03-01')
        with self.assertRaises(CommandError):
            self.load()
        self.assertEqual(Formacion.objects.count(), 1)
