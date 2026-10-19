from io import StringIO

from django.core.management import call_command, CommandError
from django.test import TestCase

from portfolio.models import Experiencia


class ApprovedExperienceTests(TestCase):
    def load(self, **options):
        call_command('load_approved_experience', stdout=StringIO(), **options)

    def test_public_experience_matches_owner_supplied_history(self):
        self.load(publish=True)
        response = self.client.get('/api/v1/experiencias/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 3)
        self.assertEqual([item['organization'] for item in data['results']],
                         ['DGES', 'Freelance', 'Sanatorio Francés'])
        self.assertEqual(data['results'][0]['startDate'], '2025-06-01')
        self.assertEqual(data['results'][0]['endDate'], '2025-11-01')
        self.assertEqual(data['results'][1]['startDate'], '2023-01-01')
        self.assertIsNone(data['results'][1]['endDate'])
        self.assertTrue(data['results'][1]['isCurrent'])
        self.assertEqual(data['results'][2]['endDate'], '2025-05-01')

    def test_draft_then_publication_does_not_duplicate_or_unpublish(self):
        self.load()
        ids = list(Experiencia.objects.values_list('pk', flat=True))
        self.assertEqual(self.client.get('/api/v1/experiencias/').json()['count'], 0)
        self.load(publish=True)
        self.load()
        self.assertEqual(list(Experiencia.objects.values_list('pk', flat=True)), ids)
        self.assertEqual(Experiencia.objects.filter(is_published=True).count(), 3)

    def test_existing_edits_are_preserved_without_partial_publication(self):
        self.load()
        Experiencia.objects.filter(organization='Sanatorio Francés').update(description='Owner edit')
        with self.assertRaises(CommandError):
            self.load(publish=True)
        self.assertEqual(Experiencia.objects.filter(is_published=True).count(), 0)
        self.assertEqual(Experiencia.objects.get(organization='Sanatorio Francés').description, 'Owner edit')

    def test_unrelated_work_history_is_not_overwritten(self):
        Experiencia.objects.create(title='Other work', organization='Other organization',
                                   description='Existing work.', start_date='2020-01-01')
        with self.assertRaises(CommandError):
            self.load()
        self.assertEqual(Experiencia.objects.count(), 1)
