import io
import json
from unittest.mock import patch
from urllib.error import HTTPError

from django.test import SimpleTestCase, override_settings

from . import contact as module


DATA = {'nombre': 'Ana Visitante', 'telefono': '+54 351 555 0101',
        'email': 'ana@example.com', 'asunto': 'Propuesta de trabajo',
        'mensaje': 'Quiero conversar sobre un proyecto de Angular.', 'website': '',
        'solicitud': 'da6d7f08-8734-4fd8-bd92-7773c8d79102'}


@override_settings(RESEND_API_KEY='synthetic-only', CONTACT_FROM_EMAIL='onboarding@resend.dev')
class ContactTests(SimpleTestCase):
    path = '/api/v1/contacto/'

    def setUp(self):
        module._attempts.clear()

    def post(self, data=None, **headers):
        return self.client.post(self.path, json.dumps(DATA if data is None else data),
                                content_type='application/json', **headers)

    @patch.object(module, 'urlopen')
    def test_real_payload_fixed_recipient_reply_to_and_idempotency(self, provider):
        provider.return_value.__enter__.return_value.status = 200
        provider.return_value.__enter__.return_value.read.return_value = b'{"id":"synthetic-email-id"}'
        result = self.post()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), {'codigo': 'MENSAJE_ENVIADO'})
        self.assertIn('no-store', result['Cache-Control'])
        request = provider.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(request.full_url, 'https://api.resend.com/emails')
        self.assertEqual(payload['to'], ['nahuel.cba.48@gmail.com'])
        self.assertEqual(payload['reply_to'], DATA['email'])
        self.assertEqual(payload['from'], 'onboarding@resend.dev')
        self.assertNotIn('html', payload)
        self.assertIn(DATA['mensaje'], payload['text'])
        self.assertIn(DATA['solicitud'], request.get_header('Idempotency-key'))

    @patch.object(module, 'deliver')
    def test_reject_invalid_inputs_header_injection_and_recipient_override(self, provider):
        for key, value in [('nombre', ''), ('nombre', 'a' * 101), ('asunto', 'x\r\nBcc: evil@example.com'),
                           ('email', 'bad'), ('telefono', 'abc1234'), ('telefono', '123'),
                           ('mensaje', 'short'), ('mensaje', 'a' * 3001), ('mensaje', '\x00' * 12),
                           ('solicitud', 'invalid'), ('email', ['a@example.com']), ('to', 'evil@example.com')]:
            with self.subTest(key=key, value=value):
                self.assertEqual(self.post({**DATA, key: value}).status_code, 400)
        for data in ([], None, 'text'):
            result = self.client.post(self.path, json.dumps(data), content_type='application/json')
            self.assertEqual(result.status_code, 400)
        self.assertEqual(self.client.post(self.path, '{"nombre":"a","nombre":"b"}',
                                         content_type='application/json').status_code, 400)
        provider.assert_not_called()

    @patch.object(module, 'deliver')
    def test_honeypot_ignores_bot_submission(self, provider):
        self.assertEqual(self.post({**DATA, 'website': 'spam.example'}).status_code, 200)
        provider.assert_not_called()

    @patch.object(module, 'deliver')
    def test_unconfigured_fails_instead_of_claiming_delivery(self, provider):
        with override_settings(RESEND_API_KEY=''):
            self.assertEqual(self.post().status_code, 503)
        provider.assert_not_called()

    @patch.object(module, 'deliver')
    def test_rate_and_concurrency_limit(self, provider):
        for _ in range(10):
            self.assertEqual(self.post().status_code, 200)
        self.assertEqual(self.post().status_code, 429)
        self.assertEqual(provider.call_count, 10)
        module._attempts.clear()
        module._sending.acquire()
        module._sending.acquire()
        try:
            self.assertEqual(self.post().status_code, 429)
        finally:
            module._sending.release()
            module._sending.release()

    @patch.object(module, 'urlopen')
    def test_provider_errors_and_malformed_success_never_claim_delivery(self, provider):
        provider.side_effect = HTTPError('https://api.resend.com/emails', 403, 'secret', {}, io.BytesIO(b'private'))
        with self.assertLogs('portfolio.contact') as logs:
            result = self.post()
        self.assertEqual(result.status_code, 503)
        self.assertNotIn('private', ''.join(logs.output))
        self.assertNotIn('secret', result.content.decode())
        provider.side_effect = None
        provider.return_value.__enter__.return_value.status = 200
        for body in (b'{}', b'not-json', b'[]'):
            provider.return_value.__enter__.return_value.read.return_value = body
            self.assertEqual(self.post().status_code, 503)

    def test_methods_origin_and_size(self):
        self.assertEqual(self.client.get(self.path).status_code, 405)
        self.assertEqual(self.client.options(self.path)['Allow'], 'POST, OPTIONS')
        self.assertEqual(self.post(HTTP_ORIGIN='https://evil.example').status_code, 403)
        self.assertEqual(self.client.post(self.path, 'a' * 16385,
                                         content_type='application/json').status_code, 413)
        self.assertEqual(self.client.post(self.path, DATA).status_code, 415)

    @override_settings(CORS_ALLOWED_ORIGINS=['http://localhost:4200'])
    def test_cors_preflight(self):
        result = self.client.options(self.path, HTTP_ORIGIN='http://localhost:4200',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST', HTTP_ACCESS_CONTROL_REQUEST_HEADERS='content-type')
        self.assertEqual(result['Access-Control-Allow-Origin'], 'http://localhost:4200')
        self.assertIn('POST', result['Access-Control-Allow-Methods'])
