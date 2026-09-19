web: gunicorn docsaya.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 60
release: python manage.py migrate --noinput && python manage.py seed && python manage.py collectstatic --noinput
