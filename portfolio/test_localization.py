from io import StringIO
from urllib.parse import parse_qs, urlparse

from django.core.management import call_command
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection

from portfolio.localization import localize_payload
from portfolio.models import Experiencia, Formacion, Perfil, Proyecto


class LocalizationTests(TestCase):
    def setUp(self):
        call_command('load_approved_experience', publish=True, stdout=StringIO())
        call_command('load_approved_education', publish=True, stdout=StringIO())

    def test_profile_translates_paragraphs_and_retains_assets_and_database(self):
        original = Perfil.objects.get().biography
        spanish = self.client.get('/api/v1/perfil/')
        english = self.client.get('/api/v1/perfil/?lang=en')
        self.assertEqual(english.status_code, 200)
        self.assertEqual(english['Content-Language'], 'en')
        self.assertEqual(spanish['Content-Language'], 'es')
        self.assertTrue(english.json()['biography'].startswith('I am a software developer'))
        self.assertEqual(len(english.json()['biography'].split('\n\n')), 3)
        self.assertEqual(english.json()['photo'], '/assets/nahuel.jpg')
        self.assertEqual(Perfil.objects.get().biography, original)
        self.assertEqual(set(spanish.json()), set(english.json()))

    def test_experience_and_education_keep_dates_organizations_and_certificate(self):
        english = self.client.get('/api/v1/experiencias/?lang=en').json()
        spanish = self.client.get('/api/v1/experiencias/').json()
        self.assertEqual(english['count'], 3)
        self.assertEqual(english['results'][0]['title'], 'Web Development Intern')
        self.assertIn('Worked with WordPress', english['results'][0]['description'])
        for es, en in zip(spanish['results'], english['results']):
            for key in ('organization', 'startDate', 'endDate', 'isCurrent'):
                self.assertEqual(es[key], en[key])
        education = self.client.get('/api/v1/formacion/?lang=en').json()['results']
        self.assertEqual(education[0]['name'], 'Higher Technical Degree in Software Development')
        self.assertIn('drive.google.com', education[1]['url'])
        self.assertEqual(Formacion.objects.get(type='certification').name, 'Junior Full Stack Developer')
        self.assertEqual(Experiencia.objects.get(organization='DGES').title, 'Pasante de desarrollo web')

    def test_projects_translate_content_and_preserve_urls_slugs_order_and_query_count(self):
        with CaptureQueriesContext(connection) as spanish_queries:
            spanish = self.client.get('/api/v1/proyectos/').json()
        with CaptureQueriesContext(connection) as english_queries:
            english = self.client.get('/api/v1/proyectos/?lang=en').json()
        self.assertEqual(len(spanish_queries), len(english_queries))
        self.assertEqual(spanish['count'], english['count'])
        for es, en in zip(spanish['results'], english['results']):
            for key in ('name', 'slug', 'image', 'technologies'):
                self.assertEqual(es[key], en[key])
            self.assertEqual([link['url'] for link in es['links']],
                             [link['url'] for link in en['links']])
            detail = self.client.get(f"/api/v1/proyectos/{en['slug']}/?lang=en")
            self.assertEqual(detail.json(), en)
        self.assertEqual(english['results'][0]['type'], 'Team project')
        self.assertEqual(english['results'][0]['links'][0]['label'], 'View demo')

    def test_language_is_preserved_through_pagination(self):
        response = self.client.get('/api/v1/tecnologias/?lang=en&page_size=3').json()
        seen = 0
        while True:
            seen += sum(len(group['technologies']) for group in response['results'])
            if response['next'] is None:
                break
            self.assertEqual(parse_qs(urlparse(response['next']).query)['lang'], ['en'])
            response = self.client.get(response['next']).json()
        self.assertEqual(seen, response['count'])

    def test_drafts_stay_private_in_both_languages_and_writes_are_rejected(self):
        draft = Proyecto.objects.first()
        draft.is_published = False
        draft.save()
        for language in ('es', 'en'):
            response = self.client.get(f'/api/v1/proyectos/?lang={language}').json()
            self.assertNotIn(draft.slug, [item['slug'] for item in response['results']])
            self.assertEqual(self.client.get(f'/api/v1/proyectos/{draft.slug}/?lang={language}').status_code, 404)
            self.assertEqual(self.client.post(f'/api/v1/experiencias/?lang={language}').status_code, 405)

    def test_unknown_language_is_rejected_and_missing_translations_use_source(self):
        self.assertEqual(self.client.get('/api/v1/perfil/?lang=fr').status_code, 400)
        payload = {'description': 'Contenido nuevo', 'slug': 'Ver demo', 'url': 'Ver demo'}
        self.assertEqual(localize_payload(payload, 'en'), payload)

    def test_errors_and_head_are_localized_without_changing_status(self):
        response = self.client.get('/api/v1/proyectos/?lang=en&page_size=0')
        self.assertEqual(response.status_code, 400)
        self.assertIn('must be an integer', response.json()['detail'])
        self.assertEqual(self.client.post('/api/v1/perfil/?lang=en').json()['detail'], 'Method not allowed.')
        head = self.client.head('/api/v1/perfil/?lang=en')
        self.assertEqual(head.status_code, 200)
        self.assertEqual(head.content, b'')
        self.assertEqual(head['Content-Language'], 'en')
