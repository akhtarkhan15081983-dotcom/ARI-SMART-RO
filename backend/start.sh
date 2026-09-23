#!/bin/sh
set -eu

python manage.py migrate --noinput
python manage.py bootstrap_admin
python manage.py reset_face_device_data
python manage.py collectstatic --noinput

exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${GUNICORN_WORKERS:-2}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --max-requests "${GUNICORN_MAX_REQUESTS:-750}" \
    --max-requests-jitter "${GUNICORN_MAX_REQUESTS_JITTER:-100}" \
    --access-logfile - \
    --error-logfile -
