"""Allowlisted diagnostics: never serialize messages, requests or tracebacks."""
import json
import logging
from datetime import datetime, timezone

from django.db import utils as database_errors


def safe_error_type(error):
    # Fixed names, including for subclasses; never use exception text or repr.
    for kind in (
        database_errors.OperationalError, database_errors.InterfaceError,
        database_errors.IntegrityError, database_errors.ProgrammingError,
        database_errors.DataError, database_errors.InternalError,
        database_errors.NotSupportedError, database_errors.DatabaseError,
        database_errors.Error, TypeError, ValueError, PermissionError,
    ):
        if isinstance(error, kind):
            return kind.__name__
    return 'UnexpectedError'


SAFE_FAILURE_TYPES = {
    'OperationalError', 'InterfaceError', 'IntegrityError', 'ProgrammingError',
    'DataError', 'InternalError', 'NotSupportedError', 'DatabaseError', 'Error',
    'TypeError', 'ValueError', 'PermissionError', 'UnexpectedError',
    'UnexpectedDatabaseResult',
}


class SafeJsonFormatter(logging.Formatter):
    def format(self, record):
        if record.name == 'portfolio.health':
            component, event = 'health', 'database_unavailable'
        elif record.name == 'portfolio.whatsapp':
            component = 'whatsapp'
            event = ('delivery_failed' if record.msg == 'whatsapp_delivery_failed'
                     else 'processing_failed')
        elif record.name == 'django.server':
            component, event = 'http', 'http_response'
        elif record.name == 'django.request':
            component, event = 'http', 'request_error'
        elif record.name.startswith('django.security'):
            component, event = 'security', 'security_error'
        elif record.name == 'django.db.backends':
            component, event = 'database', 'database_error'
        else:
            component, event = 'backend', 'backend_error'
        payload = {
            'timestamp': datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            'level': logging.getLevelName(record.levelno) if record.levelno in (
                logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL
            ) else 'UNKNOWN',
            'component': component, 'event': event,
        }
        failure_type = getattr(record, 'failure_type', None)
        if record.exc_info and isinstance(record.exc_info[1], BaseException):
            failure_type = safe_error_type(record.exc_info[1])
        if isinstance(failure_type, str) and failure_type in SAFE_FAILURE_TYPES:
            payload['errorType'] = failure_type
        status = getattr(record, 'status_code', None)
        if type(status) is int and 100 <= status <= 599:
            payload['statusCode'] = status
        if record.name == 'portfolio.whatsapp':
            for attribute, key in (('meta_code', 'metaCode'), ('meta_subcode', 'metaSubcode')):
                value = getattr(record, attribute, None)
                if type(value) is int and 0 <= value <= 2147483647:
                    payload[key] = value
        # Deliberately don't call getMessage()/formatException(): arbitrary
        # messages, args, extras and tracebacks may contain credentials or PII.
        return json.dumps(payload, ensure_ascii=True)
