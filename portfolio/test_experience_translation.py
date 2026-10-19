from io import StringIO

from django.core.management import call_command, CommandError
from django.test import TestCase

from portfolio.models import Experiencia
from portfolio.management.commands.load_approved_experience import (
    APPROVED_EXPERIENCE, ORIGINAL_EXPERIENCE,
)


class ExperienceTranslationTests(TestCase):
    def setUp(self):
        for item in ORIGINAL_EXPERIENCE:
            Experiencia.objects.create(**item, is_published=True)

    def translate(self):
        call_command('translate_approved_experience', stdout=StringIO())

    def test_translation_preserves_identity_dates_order_and_publication(self):
        ids = list(Experiencia.objects.values_list('pk', flat=True))
        self.translate()
        self.translate()
        self.assertEqual(list(Experiencia.objects.values_list('pk', flat=True)), ids)
        for expected in APPROVED_EXPERIENCE:
            item = Experiencia.objects.get(organization=expected['organization'])
            self.assertTrue(item.is_published)
            for key, value in expected.items():
                self.assertEqual(getattr(item, key), value)
        response = self.client.get('/api/v1/experiencias/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['title'] for item in response.json()['results']],
                         [item['title'] for item in APPROVED_EXPERIENCE])

    def test_owner_edit_aborts_without_partial_translation(self):
        Experiencia.objects.filter(organization='Sanatorio Francés').update(description='Edición propia')
        with self.assertRaises(CommandError):
            self.translate()
        self.assertEqual(Experiencia.objects.get(organization='DGES').title,
                         ORIGINAL_EXPERIENCE[0]['title'])

    def test_drafts_stay_unpublished(self):
        Experiencia.objects.update(is_published=False)
        self.translate()
        self.assertFalse(Experiencia.objects.filter(is_published=True).exists())
