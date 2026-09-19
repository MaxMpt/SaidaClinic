#!/bin/sh
set -e
python manage.py migrate --noinput
python manage.py seed
python manage.py collectstatic --noinput
exec gunicorn docsaya.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 60
