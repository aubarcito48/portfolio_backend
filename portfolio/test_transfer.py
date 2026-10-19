from io import StringIO
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase

from portfolio.transfer import canonical_fixture, fixture_summary


def technology(pk=1):
    return {'model': 'portfolio.tecnologia', 'pk': pk, 'fields': {
        'name': 'Synthetic', 'category': 'Test', 'url': 'https://example.test',
        'order': 0, 'is_published': False,
    }}


class TransferValidationTests(SimpleTestCase):
    def test_internal_models_are_rejected(self):
        for label in ('auth.user', 'auth.permission', 'sessions.session', 'contenttypes.contenttype'):
            with self.subTest(label=label), self.assertRaises(CommandError):
                canonical_fixture([{'model': label, 'pk': 1, 'fields': {}}])

    def test_duplicate_primary_keys_and_unknown_fields_are_rejected(self):
        with self.assertRaises(CommandError):
            canonical_fixture([technology(), technology()])
        record = technology()
        record['fields']['private_extra'] = 'must not leak'
        with self.assertRaises(CommandError):
            canonical_fixture([record])

    def test_counts_hashes_and_order_independence_include_drafts(self):
        records = [technology(1), technology(2)]
        expected = fixture_summary(records)
        self.assertEqual(expected['counts']['portfolio.tecnologia'], 2)
        self.assertEqual(expected, fixture_summary(list(reversed(records))))
        records[0]['fields']['is_published'] = True
        self.assertNotEqual(expected['valuesAndRelationsSha256'],
                            fixture_summary(records)['valuesAndRelationsSha256'])

    def test_target_actions_refuse_local_settings_before_any_query(self):
        for action in ('preflight', 'import-new', 'compare'):
            with self.subTest(action=action), self.assertRaises(CommandError):
                call_command('transfer_portfolio', action, file='backups/not-read.json',
                             stdout=StringIO())

    def test_export_cannot_overwrite_or_escape_private_directory(self):
        for path in ('README.md', 'config/settings.py'):
            with self.subTest(path=path), self.assertRaises(CommandError):
                call_command('transfer_portfolio', 'export', file=path, stdout=StringIO())
