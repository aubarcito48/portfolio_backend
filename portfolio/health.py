import logging

from django.db import Error, connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache

from config.safe_logging import safe_error_type
from portfolio.views import public_read_only


logger = logging.getLogger('portfolio.health')


@never_cache
@public_read_only
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            available = cursor.fetchone() == (1,)
    except Error as error:
        logger.error('database_unavailable', extra={
            'failure_type': safe_error_type(error), 'status_code': 503,
        })
        available = False
    else:
        if not available:
            logger.error('database_unavailable', extra={
                'failure_type': 'UnexpectedDatabaseResult', 'status_code': 503,
            })
    return JsonResponse(
        {'status': 'ok' if available else 'unavailable'},
        status=200 if available else 503,
    )
