from django.core.management.base import CommandError
from django.test import TestCase

from .management.commands.load_curriculum_vitae import CV, CV_EN, load_cv
from .models import Enlace


class CurriculumLinkTests(TestCase):
    def test_english_cv_preserves_spanish_and_is_available_in_both_api_languages(self):
        spanish, _ = load_cv()
        before = list(Enlace.objects.values())
        english, created = load_cv('en')
        self.assertTrue(created)
        self.assertEqual(list(Enlace.objects.exclude(pk=english.pk).values()), before)
        for language in ('es', 'en'):
            result = self.client.get('/api/v1/enlaces/', {'lang': language}).json()['results']
            self.assertIn(CV, result)
            self.assertIn(CV_EN, result)
        repeated, created = load_cv('en')
        self.assertFalse(created)
        self.assertEqual(repeated.pk, english.pk)
        spanish.refresh_from_db()
        self.assertEqual(spanish.url, CV['url'])

    def test_existing_model_supports_cv_and_public_api_returns_it_in_order(self):
        before = list(Enlace.objects.values())
        link, created = load_cv()
        self.assertTrue(created)
        link.full_clean()
        self.assertEqual(list(Enlace.objects.exclude(pk=link.pk).values()), before)
        for language in ('es', 'en'):
            result = self.client.get('/api/v1/enlaces/', {'lang': language}).json()['results']
            self.assertEqual(result[-1], CV)
        repeated, created = load_cv()
        self.assertFalse(created)
        self.assertEqual(repeated.pk, link.pk)

    def test_edited_cv_is_not_overwritten_or_duplicated(self):
        link, _ = load_cv()
        link.url = 'https://example.com/new-cv.pdf'
        link.save()
        with self.assertRaises(CommandError):
            load_cv()
        link.refresh_from_db()
        self.assertEqual(link.url, 'https://example.com/new-cv.pdf')
        self.assertEqual(Enlace.objects.filter(type='cv').count(), 1)
