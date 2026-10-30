"""Keep webhook verification tokens out of Gunicorn access logs."""
# U is the path without its query string; r includes the full secret-bearing URL.
access_log_format = '%(h)s %(m)s %(U)s %(s)s'
