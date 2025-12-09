#!/bin/sh
set -e

cd /app

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
# Ensure staticfiles directory exists
mkdir -p /app/staticfiles

# Collect static files
python manage.py collectstatic --noinput

# Verify files were collected
if [ -f "/app/staticfiles/css/base.css" ]; then
    echo "✓ Static files collected successfully"
else
    echo "✗ WARNING: base.css not found in staticfiles!"
    ls -la /app/staticfiles/ 2>/dev/null | head -5 || echo "staticfiles directory is empty"
fi

echo "Starting gunicorn..."
gunicorn config.wsgi:application --bind 0.0.0.0:8000
