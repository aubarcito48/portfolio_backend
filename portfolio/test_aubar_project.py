from django.core.management.base import CommandError
from django.db import transaction
from django.test import TestCase

from .localization import localize_payload
from .management.commands.load_aubar_bot import PROJECT, load_project
from .models import Proyecto, Tecnologia


class AubarProjectTests(TestCase):
    def setUp(self):
        self.python = Tecnologia.objects.get(name='Python')
        self.original_projects = list(Proyecto.objects.values())

    def test_load_is_idempotent_and_preserves_existing_projects(self):
        with transaction.atomic():
            project, created = load_project(publish=True)
            self.assertTrue(created)
            repeated, created = load_project(publish=True)
            self.assertFalse(created)
            self.assertEqual(repeated.pk, project.pk)
            self.assertEqual(list(Proyecto.objects.exclude(pk=project.pk).values()), self.original_projects)
            self.assertEqual(set(project.technologies.values_list('name', flat=True)), {'Python', 'C++', 'Arduino', 'ESP32'})
            self.assertEqual(project.repository_url, 'https://github.com/aubarcito48/aubar-bot')
            self.assertEqual(project.demo_url, '')

    def test_existing_edits_are_never_overwritten(self):
        with transaction.atomic():
            project, _ = load_project(publish=True)
        project.title = 'Owner edited this title'
        project.save()
        with self.assertRaises(CommandError), transaction.atomic():
            load_project(publish=True)
        project.refresh_from_db()
        self.assertEqual(project.title, 'Owner edited this title')

    def test_new_copy_is_translated_without_modifying_urls(self):
        with transaction.atomic():
            project, _ = load_project(publish=True)
            payload = project.to_public_dict()
        english = localize_payload(payload, 'en')
        self.assertTrue(english['description'].startswith('Desktop assistant'))
        self.assertEqual(english['links'][0]['url'], PROJECT['repository_url'])
        self.assertEqual(english['type'], 'Personal project · Hardware and AI')
