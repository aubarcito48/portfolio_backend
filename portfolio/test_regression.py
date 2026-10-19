from io import StringIO
from unittest.mock import patch

from django.core.management import call_command, CommandError
from django.test import SimpleTestCase, TestCase

from portfolio.management.commands.load_portfolio_e2e_data import validate_e2e_database
from portfolio.models import Enlace, Experiencia, Formacion, Proyecto, Tecnologia


class E2EDatabaseSafetyTests(SimpleTestCase):
    def test_only_explicit_disposable_test_database_is_allowed(self):
        valid = dict(environment='test', database_name='portfolio_e2e_fixture',
                     e2e_database='portfolio_e2e_fixture',
                     development_database='portfolio', test_database='test_portfolio')
        validate_e2e_database(**valid)
        for changes in (
            {'environment': 'development'}, {'environment': 'production'},
            {'e2e_database': None}, {'e2e_database': 'another_database'},
            {'development_database': None},
            {'development_database': 'portfolio_e2e_fixture'},
            {'test_database': 'portfolio_e2e_fixture'},
            {'database_name': 'portfolio', 'e2e_database': 'portfolio'},
        ):
            with self.subTest(changes=changes), self.assertRaises(CommandError):
                validate_e2e_database(**(valid | changes))

    def test_command_refuses_unsafe_database_before_writing(self):
        # SimpleTestCase forbids DB queries: the guard must run before any write.
        with patch.dict('os.environ', {'PORTFOLIO_E2E_DATABASE': ''}):
            with self.assertRaises(CommandError):
                call_command('load_portfolio_e2e_data', stdout=StringIO())


class E2EFixtureTests(TestCase):
    def load_fixture(self):
        # Django has already isolated this connection in its own test database.
        with patch('portfolio.management.commands.load_portfolio_e2e_data.validate_e2e_database'):
            call_command('load_portfolio_e2e_data', stdout=StringIO())

    def test_repeated_seed_keeps_ids_and_drafts_out_of_all_public_resources(self):
        self.load_fixture()
        models = (Enlace, Experiencia, Formacion, Proyecto, Tecnologia)
        ids = {model: list(model.objects.values_list('pk', flat=True)) for model in models}
        self.load_fixture()
        for model in models:
            self.assertEqual(list(model.objects.values_list('pk', flat=True)), ids[model])
            self.assertTrue(model.objects.filter(is_published=False).exists())
        for resource in ('tecnologias', 'experiencias', 'formacion', 'proyectos', 'enlaces'):
            response = self.client.get(f'/api/v1/{resource}/?page_size=100')
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('TK15 Draft', response.content.decode())
        for resource in ('experiencias', 'formacion'):
            self.assertEqual(self.client.get(f'/api/v1/{resource}/').json()['count'], 1)
        self.assertEqual(self.client.get('/api/v1/proyectos/tk15-draft-project/').status_code, 404)

    def test_seed_failure_rolls_back_changes(self):
        before = list(Tecnologia.objects.values())
        with patch('portfolio.management.commands.load_portfolio_e2e_data.validate_e2e_database'), \
             patch('portfolio.management.commands.load_portfolio_e2e_data.Formacion.objects.update_or_create',
                   side_effect=RuntimeError('injected failure')):
            with self.assertRaisesRegex(RuntimeError, 'injected failure'):
                call_command('load_portfolio_e2e_data', stdout=StringIO())
        self.assertEqual(list(Tecnologia.objects.values()), before)
        self.assertFalse(Experiencia.objects.filter(title__startswith='TK15').exists())
        self.assertFalse(Proyecto.objects.filter(slug='tk15-draft-project').exists())
