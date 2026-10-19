import runpy
from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.core.mail import mailers, send_mail
from django.core.mail.backends.dummy import EmailBackend as DisabledEmailBackend
from django.test import RequestFactory, SimpleTestCase, override_settings


def deployment_settings(environment):
    # Import configuration without touching any .env file or connecting to a DB.
    with patch.dict('os.environ', {
        'DJANGO_ENVIRONMENT': environment,
        'DJANGO_DEBUG': 'False' if environment != 'development' else 'True',
        'DJANGO_ALLOWED_HOSTS': 'backend.example.test',
    }), patch('dotenv.load_dotenv'):
        return runpy.run_path(str(settings.BASE_DIR / 'config' / 'settings.py'))


class DeploymentSettingsTests(SimpleTestCase):
    def test_https_and_secure_cookies_are_enabled_only_in_production(self):
        production = deployment_settings('production')
        self.assertEqual(production['SECURE_PROXY_SSL_HEADER'],
                         ('HTTP_X_FORWARDED_PROTO', 'https'))
        self.assertTrue(production['SESSION_COOKIE_SECURE'])
        self.assertTrue(production['CSRF_COOKIE_SECURE'])
        for environment in ('development', 'test'):
            config = deployment_settings(environment)
            self.assertNotIn('SECURE_PROXY_SSL_HEADER', config)
            self.assertNotIn('SESSION_COOKIE_SECURE', config)
            self.assertNotIn('CSRF_COOKIE_SECURE', config)

    def test_https_forwarding_is_recognized_without_redirecting_readiness(self):
        with override_settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https')):
            request = RequestFactory().get('/health/', HTTP_X_FORWARDED_PROTO='https')
            self.assertTrue(request.is_secure())
            self.assertFalse(RequestFactory().get('/health/').is_secure())

    def test_disabled_production_mail_does_not_send_or_print_content(self):
        config = deployment_settings('production')
        self.assertEqual(config['SILENCED_SYSTEM_CHECKS'], ['mail.E001'])
        self.assertEqual(config['MAILERS']['default']['BACKEND'],
                         'django.core.mail.backends.dummy.EmailBackend')
        output = StringIO()
        with override_settings(MAILERS=config['MAILERS']), \
                patch('smtplib.SMTP') as smtp, patch('sys.stdout', output):
            self.assertIsInstance(mailers.default, DisabledEmailBackend)
            send_mail('private subject', 'private body',
                      'sender@example.test', ['recipient@example.test'])
        smtp.assert_not_called()
        self.assertEqual(output.getvalue(), '')

    def test_development_mail_remains_console_without_silencing_deploy_checks(self):
        config = deployment_settings('development')
        self.assertEqual(config['MAILERS']['default']['BACKEND'],
                         'django.core.mail.backends.console.EmailBackend')
        self.assertNotIn('SILENCED_SYSTEM_CHECKS', config)

    def test_whitenoise_precedes_sessions_and_static_root_is_defined(self):
        self.assertEqual(settings.STATIC_ROOT, settings.BASE_DIR / 'staticfiles')
        self.assertEqual(settings.STATIC_URL, '/static/')
        self.assertEqual(settings.MIDDLEWARE[:2], [
            'django.middleware.security.SecurityMiddleware',
            'whitenoise.middleware.WhiteNoiseMiddleware',
        ])
