#!/bin/sh
set -e

cd /app

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput || true

echo "Starting gunicorn..."
gunicorn config.wsgi:application --bind 0.0.0.0:8000
