"""No calls to Meta/Groq, no real phone numbers or production databases."""
import hashlib
import hmac
import io
import json
import logging
import time
from urllib.error import HTTPError
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from . import whatsapp as wa
from .aubar_service import AubarUnavailable
from config.safe_logging import SafeJsonFormatter


CONFIG = dict(WHATSAPP_ENABLED=True, WHATSAPP_VERIFY_TOKEN='synthetic-verify',
              WHATSAPP_APP_SECRET='synthetic-secret', WHATSAPP_ACCESS_TOKEN='synthetic-access',
              WHATSAPP_PHONE_NUMBER_ID='12345', WHATSAPP_GRAPH_VERSION='v99.0')


def message(text=None, phone='15555550101', identifier='test-message'):
    return {'from': phone, 'id': identifier, 'type': 'text', 'timestamp': str(int(time.time())),
            'text': {'body': text if text is not None else next(iter(wa.TRIGGERS))}}


def payload(messages=None, phone_id='12345'):
    return {'object': 'whatsapp_business_account', 'entry': [{'changes': [{'field': 'messages',
            'value': {'metadata': {'phone_number_id': phone_id},
                      'messages': messages if messages is not None else [message()]}}]}]}


@override_settings(**CONFIG)
class WebhookTests(SimpleTestCase):
    path = '/api/v1/whatsapp/webhook/'

    def post(self, data, signature=None):
        body = json.dumps(data).encode()
        signature = signature or 'sha256=' + hmac.new(b'synthetic-secret', body, hashlib.sha256).hexdigest()
        return self.client.post(self.path, body, content_type='application/json',
                                HTTP_X_HUB_SIGNATURE_256=signature)

    def test_verification_and_disabled_switch(self):
        response = self.client.get(self.path, {'hub.mode': 'subscribe',
            'hub.verify_token': 'synthetic-verify', 'hub.challenge': 'challenge-123'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'challenge-123')
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(self.client.get(self.path).status_code, 403)
        with override_settings(WHATSAPP_ENABLED=False):
            self.assertEqual(self.post(payload()).status_code, 404)

    @patch.object(wa, 'enqueue', return_value=True)
    def test_valid_signature_queues_without_generating_or_sending(self, queue):
        with patch.object(wa, 'answer') as ai, patch.object(wa, 'send_text') as send:
            self.assertEqual(self.post(payload()).status_code, 200)
            self.assertEqual(queue.call_args.args[0][0]['from'], '15555550101')
            ai.assert_not_called()
            send.assert_not_called()
        queue.reset_mock()
        self.assertEqual(self.post(payload(), 'sha256=wrong').status_code, 403)
        queue.assert_not_called()

    @patch.object(wa, 'enqueue')
    def test_other_number_statuses_media_and_stale_messages_are_ignored(self, queue):
        stale = message()
        stale['timestamp'] = str(int(time.time()) - 600)
        for data in (payload(phone_id='98765'), payload([]), payload([stale]),
                     payload([{'type': 'image'}]), payload([message('x' * 1201)])):
            self.assertEqual(self.post(data).status_code, 200)
        queue.assert_not_called()

    @patch.object(wa, 'enqueue', return_value=False)
    def test_busy_queue_requests_retry(self, queue):
        self.assertEqual(self.post(payload()).status_code, 503)

    def test_invalid_methods_and_shapes(self):
        self.assertEqual(self.client.put(self.path).status_code, 405)
        self.assertEqual(self.client.post(self.path, 'x', content_type='text/plain').status_code, 415)
        self.assertEqual(self.client.post(self.path, 'x' * 262145,
                                         content_type='application/json').status_code, 413)
        self.assertEqual(self.post({'object': 'whatsapp_business_account', 'entry': [None]}).status_code, 400)
        self.assertEqual(self.post(payload([dict(message(), text=None)])).status_code, 400)


@override_settings(**CONFIG)
class ConversationTests(SimpleTestCase):
    def setUp(self):
        wa._sessions.clear()
        wa._rate.clear()
        wa._seen.clear()

    @patch.object(wa, 'send_text')
    @patch.object(wa, 'answer', return_value='Published project information.')
    def test_exact_activation_english_spanish_and_sender_isolation(self, ai, send):
        for text in ('hola', next(iter(wa.TRIGGERS)).lower(), next(iter(wa.TRIGGERS)) + ' '):
            wa.process_message(message(text))
        send.assert_not_called()
        for trigger, language in wa.TRIGGERS.items():
            wa.process_message(message(trigger))
            self.assertEqual(wa._sessions['15555550101'].language, language)
            self.assertEqual(send.call_args.args[1], wa.WELCOME[language])
        ai.assert_not_called()
        wa.process_message(message('What projects?', phone='15555550102'))
        ai.assert_not_called()
        wa.process_message(message('What projects?'))
        ai.assert_called_once_with('What projects?', [], 'en')

    @patch.object(wa, 'send_text')
    @patch.object(wa, 'answer')
    def test_stop_expiration_and_restart_require_activation(self, ai, send):
        wa.process_message(message())
        wa.process_message(message('HUMANO'))
        self.assertNotIn('15555550101', wa._sessions)
        wa.process_message(message('hola'))
        ai.assert_not_called()
        wa.process_message(message())
        wa._sessions['15555550101'].expires = time.time() - 1
        wa.process_message(message('pregunta'))
        ai.assert_not_called()

    @patch.object(wa, 'send_text')
    @patch.object(wa, 'answer', return_value='a' * 4000)
    def test_rate_history_and_provider_failure_are_bounded(self, ai, send):
        wa.process_message(message())
        for _ in range(7):
            wa.process_message(message('x' * 1200))
        self.assertEqual(ai.call_count, 4)
        history = wa._sessions['15555550101'].history
        self.assertLessEqual(len(history), 8)
        self.assertLessEqual(sum(len(item['content']) for item in history), 6000)
        wa._rate.clear()
        wa._sessions['15555550101'].requests.clear()
        ai.side_effect = AubarUnavailable()
        wa.process_message(message('pregunta'))
        self.assertIn('Ahora no puedo responder', send.call_args.args[1])

    def test_queue_deduplicates_and_rolls_back_on_submission_error(self):
        with patch.object(wa, '_executor') as executor:
            self.assertTrue(wa.enqueue([message(), message()]))
            self.assertTrue(wa.enqueue([message()]))
            executor.submit.assert_called_once()
            self.assertEqual(len(executor.submit.call_args.args[1]), 1)
            wa._slots.release()  # Mocked executor did not run the real batch's finally.
            executor.submit.side_effect = RuntimeError()
            self.assertFalse(wa.enqueue([message(identifier='different')]))
            self.assertNotIn('different', wa._seen)

    def test_queue_saturation_never_admits_a_message(self):
        slots = MagicMock()
        slots.acquire.return_value = False
        with patch.object(wa, '_slots', slots):
            self.assertFalse(wa.enqueue([message()]))
        self.assertEqual(len(wa._seen), 0)

    @patch.object(wa, 'urlopen')
    def test_send_uses_fixed_graph_host_and_backend_token(self, http):
        http.return_value.__enter__.return_value.status = 200
        wa.send_text('15555550101', 'Hello')
        request = http.call_args.args[0]
        self.assertEqual(request.full_url, 'https://graph.facebook.com/v99.0/12345/messages')
        self.assertEqual(request.get_header('Authorization'), 'Bearer synthetic-access')
        self.assertEqual(json.loads(request.data)['text']['body'], 'Hello')

    @patch.object(wa, 'process_message', side_effect=RuntimeError('private data'))
    def test_background_failure_is_sanitized_and_capacity_is_released(self, process):
        with patch.object(wa, '_slots') as slots, patch.object(wa, 'logger') as log:
            wa._run_batch([message()])
            slots.release.assert_called_once()
            log.error.assert_called_once_with('whatsapp_processing_failed',
                extra={'failure_type': 'UnexpectedError'})

    @patch.object(wa, 'urlopen')
    def test_meta_rejection_exposes_only_allowlisted_numeric_diagnostics(self, http):
        raw = {'error': {'code': 190, 'error_subcode': 463, 'message': 'private-token-and-phone'}}
        http.side_effect = HTTPError('https://graph.facebook.com', 401, 'private', {},
                                     io.BytesIO(json.dumps(raw).encode()))
        with self.assertRaises(wa.WhatsAppSendError) as caught:
            wa.send_text('15555550101', 'Hello')
        error = caught.exception
        self.assertEqual((error.status, error.code, error.subcode), (401, 190, 463))
        with patch.object(wa, 'process_message', side_effect=error), self.assertLogs('portfolio.whatsapp') as logs:
            wa._slots.acquire()
            wa._run_batch([message()])
        formatted = SafeJsonFormatter().format(logs.records[0])
        result = json.loads(formatted)
        self.assertEqual(result['event'], 'delivery_failed')
        self.assertEqual(result['metaCode'], 190)
        self.assertEqual(result['metaSubcode'], 463)
        self.assertEqual(result['statusCode'], 401)
        self.assertNotIn('private', formatted)
        record = logging.LogRecord('portfolio.whatsapp', logging.ERROR, '', 0,
                                   'whatsapp_delivery_failed', (), None)
        record.meta_code = 'secret-value'
        self.assertNotIn('secret-value', SafeJsonFormatter().format(record))
