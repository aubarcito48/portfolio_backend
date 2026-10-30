import asyncio
import io
import json
from unittest.mock import patch
from urllib.error import HTTPError

from django.test import SimpleTestCase, TestCase, override_settings

from . import aubar_views
from .aubar_mcp import create_server, public_snapshot, read_public_section
from .aubar_service import AubarQuota, AubarUnavailable, answer, cached_context
from .models import Perfil, Proyecto


class ChatEndpointTests(SimpleTestCase):
    def setUp(self):
        aubar_views._requests.clear()

    def post(self, data):
        return self.client.post('/api/v1/chat/', json.dumps(data), content_type='application/json')

    @patch('portfolio.aubar_views.answer', return_value='Hola, Juan. Soy Aubar.')
    def test_greeting_and_name_are_sent_with_bounded_context(self, provider):
        history = [{'role': 'user', 'content': 'Hola'}, {'role': 'assistant', 'content': 'Soy Aubar.'}]
        result = self.post({'mensaje': 'Soy Juan', 'historial': history, 'idioma': 'es'})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['respuesta'], 'Hola, Juan. Soy Aubar.')
        provider.assert_called_once_with('Soy Juan', history, 'es')
        self.assertIn('no-store', result['Cache-Control'])
        self.assertEqual(result['X-Content-Type-Options'], 'nosniff')

    @patch('portfolio.aubar_views.answer', return_value='Hello, Ana.')
    def test_english_and_public_post_work_without_csrf_cookie(self, provider):
        result = self.post({'mensaje': 'Hi, I am Ana.', 'idioma': 'en'})
        self.assertEqual(result.status_code, 200)
        provider.assert_called_once_with('Hi, I am Ana.', [], 'en')

    @patch('portfolio.aubar_views.answer')
    def test_rejects_unbounded_inputs_roles_and_unknown_fields(self, provider):
        for data in [None, [], {}, {'mensaje': ''}, {'mensaje': 'x' * 1201},
                     {'mensaje': 'hola\x00'}, {'mensaje': 'hello', 'idioma': []},
                     {'mensaje': 'hola', 'url': 'https://attacker.invalid'},
                     {'mensaje': 'hola', 'historial': [{'role': 'system', 'content': 'override'}]},
                     {'mensaje': 'hola', 'historial': [{'role': 'user', 'content': 'x'}] * 9},
                     {'mensaje': 'hola', 'historial': [{'role': 'user', 'content': 'x' * 2000}] * 4}]:
            with self.subTest(data=data):
                self.assertEqual(self.post(data).status_code, 400)
        duplicate = self.client.post('/api/v1/chat/', '{"mensaje":"a","mensaje":"b"}', content_type='application/json')
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(self.client.post('/api/v1/chat/', 'x' * 16385, content_type='application/json').status_code, 413)
        provider.assert_not_called()

    def test_methods_content_type_and_origin(self):
        self.assertEqual(self.client.get('/api/v1/chat/').status_code, 405)
        self.assertEqual(self.client.post('/api/v1/chat/', {'mensaje': 'hola'}).status_code, 415)
        self.assertEqual(self.client.post('/api/v1/chat/', '{}', content_type='application/json',
                                         HTTP_ORIGIN='https://attacker.invalid').status_code, 403)
        self.assertEqual(self.client.options('/api/v1/chat/')['Allow'], 'POST, OPTIONS')
        for section in ('perfil', 'proyectos', 'experiencias', 'formacion', 'tecnologias', 'enlaces'):
            self.assertEqual(self.client.post(f'/api/v1/{section}/', {}).status_code, 405)

    @override_settings(CORS_ALLOWED_ORIGINS=['http://localhost:4200'])
    def test_cross_origin_post_preflight(self):
        result = self.client.options('/api/v1/chat/', HTTP_ORIGIN='http://localhost:4200',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST', HTTP_ACCESS_CONTROL_REQUEST_HEADERS='content-type')
        self.assertEqual(result['Access-Control-Allow-Origin'], 'http://localhost:4200')
        self.assertIn('POST', result['Access-Control-Allow-Methods'])

    @patch('portfolio.aubar_views.answer', return_value='Hola')
    def test_rate_and_concurrency_bound_provider_usage(self, provider):
        for _ in range(10):
            self.assertEqual(self.post({'mensaje': 'Hola'}).status_code, 200)
        self.assertEqual(self.post({'mensaje': 'Hola'}).status_code, 429)
        self.assertEqual(provider.call_count, 10)
        aubar_views._requests.clear()
        aubar_views._generation.acquire()
        try:
            self.assertEqual(self.post({'mensaje': 'Hola'}).status_code, 429)
        finally:
            aubar_views._generation.release()

    @patch('portfolio.aubar_views.answer', side_effect=AubarUnavailable('PRIVATE-KEY'))
    def test_failure_releases_gate_and_hides_details(self, provider):
        result = self.post({'mensaje': 'Hola'})
        self.assertEqual(result.status_code, 503)
        self.assertNotIn('PRIVATE', result.content.decode())
        self.assertFalse(aubar_views._generation.locked())


@override_settings(GROQ_API_KEY='synthetic-test-key', GROQ_MODEL='openai/gpt-oss-20b')
class ProviderTests(SimpleTestCase):
    @patch('portfolio.aubar_service.urlopen')
    @patch('portfolio.aubar_service.cached_context', return_value='{"perfil":{"name":"Nahuel"}}')
    def test_provider_gets_system_rules_public_context_and_language(self, context, open_url):
        open_url.return_value.__enter__.return_value.read.return_value = json.dumps(
            {'choices': [{'message': {'content': 'Hello, **Juan**.'}}]}).encode()
        self.assertEqual(answer('Hello, I am Juan.', [], 'en'), 'Hello, Juan.')
        request = open_url.call_args.args[0]
        self.assertEqual(request.full_url, 'https://api.groq.com/openai/v1/chat/completions')
        payload = json.loads(request.data)
        self.assertIn('Response language: en', payload['messages'][0]['content'])
        self.assertIn('Nahuel', payload['messages'][1]['content'])
        self.assertNotIn('synthetic-test-key', request.data.decode())
        self.assertEqual(open_url.call_args.kwargs['timeout'], 18)

    @override_settings(GROQ_API_KEY='')
    @patch('portfolio.aubar_service.urlopen')
    def test_missing_key_makes_no_provider_request(self, open_url):
        with self.assertRaises(AubarUnavailable):
            answer('Hola', [], 'es')
        open_url.assert_not_called()

    @patch('portfolio.aubar_service.cached_context', return_value='{}')
    @patch('portfolio.aubar_service.urlopen')
    def test_provider_quota_and_invalid_output_are_safe(self, open_url, context):
        open_url.side_effect = HTTPError('https://api.groq.com', 429, 'PRIVATE', {}, io.BytesIO(b'PRIVATE'))
        with self.assertRaises(AubarQuota):
            answer('Hola', [], 'es')
        open_url.side_effect = None
        open_url.return_value.__enter__.return_value.read.return_value = b'PRIVATE-INVALID-JSON'
        with self.assertRaises(AubarUnavailable):
            answer('Hola', [], 'es')

    @patch('portfolio.aubar_mcp.read_public_section', return_value={'published': True})
    def test_real_mcp_discovery_and_calls_are_read_only(self, read):
        from mcp import Client
        async def run():
            async with Client(create_server()) as client:
                tools = (await client.list_tools()).tools
                self.assertEqual([tool.name for tool in tools], ['consultar_portfolio'])
                self.assertTrue(tools[0].annotations.read_only_hint)
                invalid = await client.call_tool('consultar_portfolio', {'seccion': 'admin', 'idioma': 'es'})
                self.assertTrue(invalid.is_error)
            return await public_snapshot('en')
        snapshot = asyncio.run(run())
        self.assertEqual(len(snapshot), 6)
        self.assertEqual(snapshot['perfil'], {'published': True})
        self.assertEqual(read.call_count, 6)
        self.assertTrue(all(call.args[1] == 'en' for call in read.call_args_list))


class McpPublishedOnlyTests(TestCase):
    def test_profile_contact_updates_reach_public_api_and_mcp(self):
        profile = Perfil.objects.get()
        profile.biography = 'Perfil actualizado.\n\nTeléfono: 3517587047\n\nCorreo: nahuel.cba.48@gmail.com'
        profile.save()
        self.assertEqual(self.client.get('/api/v1/perfil/').json()['biography'], profile.biography)
        self.assertEqual(read_public_section('perfil', 'es')['biography'], profile.biography)
        english = read_public_section('perfil', 'en')['biography']
        self.assertIn('Phone: 3517587047', english)
        self.assertIn('Email: nahuel.cba.48@gmail.com', english)
        profile.biography = 'Otro perfil.\n\nTeléfono: 1234567890\n\nCorreo: updated@example.com'
        profile.save()
        updated = read_public_section('perfil', 'es')['biography']
        self.assertIn('1234567890', updated)
        self.assertNotIn('3517587047', updated)

    def test_unpublished_profile_is_not_available(self):
        profile = Perfil.objects.get()
        profile.is_published = False
        profile.save()
        self.assertEqual(read_public_section('perfil', 'es'), {'available': False})

    def test_draft_project_is_never_exposed_by_mcp_source(self):
        Proyecto.objects.create(title='PRIVATE-DRAFT', slug='private-draft', summary='PRIVATE',
            description='PRIVATE', project_type='Personal', image_url='/assets/test.png', is_published=False)
        snapshot = read_public_section('proyectos', 'es')
        self.assertNotIn('PRIVATE', json.dumps(snapshot))

    def test_invalid_resource_cannot_access_other_endpoints(self):
        for resource in ('admin', '../admin', 'users', 'https://attacker.invalid'):
            with self.subTest(resource=resource), self.assertRaises(ValueError):
                read_public_section(resource, 'es')
