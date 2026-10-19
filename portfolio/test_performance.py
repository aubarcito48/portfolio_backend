from io import StringIO
from unittest.mock import patch

from django.core.management import call_command, CommandError
from django.db.models import Prefetch
from django.test import SimpleTestCase, TestCase

from portfolio.models import EnlaceProyecto, Proyecto, Tecnologia


class PerformanceFixtureSafetyTests(SimpleTestCase):
    def test_seed_rejects_unsafe_database_before_any_query(self):
        with patch.dict('os.environ', {'PORTFOLIO_E2E_DATABASE': ''}):
            with self.assertRaises(CommandError):
                call_command('load_portfolio_performance_data', stdout=StringIO())


class ProjectQueryBudgetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with patch('portfolio.management.commands.load_portfolio_performance_data.validate_e2e_database'):
            call_command('load_portfolio_performance_data', stdout=StringIO())

    def test_project_list_query_count_is_constant_and_preserves_content(self):
        for page_size in (1, 20, 100):
            with self.subTest(page_size=page_size), self.assertNumQueries(4):
                response = self.client.get(f'/api/v1/proyectos/?page_size={page_size}')
                payload = response.json()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(payload['count'], 100)
            self.assertEqual(len(payload['results']), page_size)
            self.assertEqual(payload['results'][0]['slug'], 'tk16-project-001')
            self.assertEqual(payload['results'][-1]['slug'], f'tk16-project-{page_size:03}')
            for project in payload['results']:
                self.assertEqual(len(project['technologies']), 5)
                self.assertEqual(len(project['links']), 3)
                self.assertNotIn('TK16 Technology 11', project['technologies'])
            self.assertEqual(payload['previous'], None)
            self.assertEqual(payload['next'] is None, page_size == 100)

    def test_second_page_and_detail_keep_query_budget_and_drafts_private(self):
        with self.assertNumQueries(4):
            payload = self.client.get('/api/v1/proyectos/?page=2').json()
        self.assertEqual(payload['results'][0]['slug'], 'tk16-project-021')
        self.assertEqual(payload['results'][-1]['slug'], 'tk16-project-040')
        with self.assertNumQueries(3):
            detail = self.client.get('/api/v1/proyectos/tk16-project-001/').json()
        self.assertEqual(len(detail['technologies']), 5)
        self.assertEqual(self.client.get('/api/v1/proyectos/tk16-project-101/').status_code, 404)

    def test_prefetched_serialization_neither_queries_nor_constructs_fallback(self):
        project = Proyecto.objects.prefetch_related(
            Prefetch('technologies', queryset=Tecnologia.objects.filter(is_published=True)
                     .order_by('order', 'id'), to_attr='published_technologies'),
            'additional_links',
        ).get(pk=1)
        manager_class = type(project.technologies)
        with patch.object(manager_class, 'filter', side_effect=AssertionError('unneeded queryset')):
            with self.assertNumQueries(0):
                payload = project.to_public_dict()
        self.assertEqual(len(payload['technologies']), 5)
        project.published_technologies = []
        with patch.object(manager_class, 'filter', side_effect=AssertionError('empty prefetch ignored')):
            with self.assertNumQueries(0):
                self.assertEqual(project.to_public_dict()['technologies'], [])

    def test_standalone_serialization_retains_filtered_ordered_fallback(self):
        project = Proyecto.objects.get(pk=1)
        with self.assertNumQueries(2):
            payload = project.to_public_dict()
        expected = list(project.technologies.filter(is_published=True)
                        .order_by('order', 'id').values_list('name', flat=True))
        self.assertEqual(payload['technologies'], expected)

    def test_fixture_is_repeatable_without_duplicating_relationships(self):
        with patch('portfolio.management.commands.load_portfolio_performance_data.validate_e2e_database'):
            call_command('load_portfolio_performance_data', stdout=StringIO())
        self.assertEqual(Proyecto.objects.filter(is_published=True).count(), 100)
        self.assertEqual(Proyecto.objects.filter(is_published=False).count(), 1)
        self.assertEqual(Proyecto.technologies.through.objects.count(), 606)
        self.assertEqual(EnlaceProyecto.objects.count(), 202)
