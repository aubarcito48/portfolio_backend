import json
import logging
from contextlib import contextmanager, ExitStack
from io import StringIO
from unittest.mock import MagicMock, patch

from django.db import DatabaseError, InterfaceError, OperationalError, connection
from django.test import RequestFactory, SimpleTestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext

from config.safe_logging import SafeJsonFormatter


CANARY = 'TK17_PRIVATE_password_cookie_token_user_host'


@contextmanager
def captured_console():
    output = StringIO()
    handlers = {handler for name in ('', 'django', 'django.server',
                                     'django.db.backends', 'portfolio.health')
                for handler in logging.getLogger(name).handlers}
    with ExitStack() as stack:
        for handler in handlers:
            if isinstance(handler, logging.StreamHandler):
                stack.enter_context(patch.object(handler, 'stream', output))
        yield output


class HealthTests(TransactionTestCase):
    def test_real_postgresql_check_is_one_read_only_query(self):
        self.assertEqual(connection.vendor, 'postgresql')
        connection.ensure_connection()
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})
        self.assertEqual([q['sql'] for q in queries], ['SELECT 1'])
        self.assertIn('no-store', response.headers['Cache-Control'])
        self.assertFalse(response.cookies)

    def test_connection_failure_is_generic_and_recovers(self):
        for kind in (OperationalError, InterfaceError, DatabaseError):
            with self.subTest(kind=kind.__name__), captured_console() as logs:
                with patch('portfolio.health.connection.cursor', side_effect=kind(CANARY)):
                    response = self.client.get('/health/?token=' + CANARY,
                                               HTTP_AUTHORIZATION='Bearer ' + CANARY,
                                               HTTP_COOKIE='sessionid=' + CANARY)
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json(), {'status': 'unavailable'})
                self.assertIn('no-store', response.headers['Cache-Control'])
                self.assertNotIn(CANARY, response.content.decode())
                self.assertNotIn(CANARY, logs.getvalue())
                records = [json.loads(line) for line in logs.getvalue().splitlines()]
                self.assertTrue(any(r.get('errorType') == kind.__name__
                                    and r['event'] == 'database_unavailable' for r in records))
            self.assertEqual(self.client.get('/health/').json(), {'status': 'ok'})

    def test_query_failure_and_unexpected_result_return_unavailable(self):
        cursor = MagicMock()
        cursor.execute.side_effect = OperationalError(CANARY)
        for fail_query in (True, False):
            with self.subTest(fail_query=fail_query), captured_console() as logs:
                if not fail_query:
                    cursor.execute.side_effect = None
                    cursor.fetchone.return_value = None
                with patch('portfolio.health.connection.cursor') as mock:
                    mock.return_value.__enter__.return_value = cursor
                    response = self.client.get('/health/')
                self.assertEqual(response.status_code, 503)
                self.assertNotIn(CANARY, logs.getvalue())
                self.assertIn('OperationalError' if fail_query else 'UnexpectedDatabaseResult',
                              logs.getvalue())

    def test_head_checks_database_and_options_does_not(self):
        with self.assertNumQueries(1):
            response = self.client.head('/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'')
        with self.assertNumQueries(0):
            response = self.client.options('/health/')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.headers['Allow'], 'GET, HEAD, OPTIONS')

    def test_write_methods_are_rejected_without_accessing_database(self):
        for method in ('post', 'put', 'patch', 'delete', 'trace'):
            with self.subTest(method=method), captured_console(), self.assertNumQueries(0):
                response = getattr(self.client, method)('/health/')
                self.assertEqual(response.status_code, 405)
                self.assertEqual(response.json(), {'detail': 'Método no permitido.'})


class SafeLoggingTests(SimpleTestCase):
    def test_configured_loggers_drop_messages_exceptions_requests_and_secrets(self):
        request = RequestFactory().get('/private/' + CANARY + '?token=' + CANARY,
                                       HTTP_AUTHORIZATION='Bearer ' + CANARY,
                                       HTTP_COOKIE='sessionid=' + CANARY)
        with captured_console() as logs:
            for name in ('django.request', 'django.server', 'django.db.backends',
                         'django.security.DisallowedHost', 'portfolio.health', CANARY):
                try:
                    raise OperationalError('postgresql://user:' + CANARY + '@private-host/db')
                except OperationalError:
                    logging.getLogger(name).error('private payload=%s', CANARY,
                                                  exc_info=True, stack_info=True, extra={
                                                      'request': request, 'status_code': 503,
                                                      'sql': CANARY, 'params': {'password': CANARY},
                                                  })
        self.assertNotIn(CANARY, logs.getvalue())
        self.assertNotIn('private-host', logs.getvalue())
        records = [json.loads(line) for line in logs.getvalue().splitlines()]
        self.assertEqual(len(records), 6)
        for record in records:
            self.assertEqual(record['errorType'], 'OperationalError')
            self.assertEqual(record['statusCode'], 503)
            self.assertEqual(set(record), {'timestamp', 'level', 'component', 'event',
                                           'errorType', 'statusCode'})

    def test_formatter_never_stringifies_arbitrary_objects_or_unknown_exception_names(self):
        class PrivateObject:
            def __str__(self):
                raise AssertionError('Sensitive object must not be evaluated')
        error_class = type(CANARY, (Exception,), {})
        record = logging.LogRecord(CANARY, logging.ERROR, CANARY, 1,
                                   PrivateObject(), (), (error_class, error_class(CANARY), None))
        record.failure_type = CANARY
        record.status_code = CANARY
        record.stack_info = CANARY
        payload = SafeJsonFormatter().format(record)
        self.assertNotIn(CANARY, payload)
        self.assertEqual(json.loads(payload)['errorType'], 'UnexpectedError')
