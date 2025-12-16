#!/bin/sh
set -e

cd /app

echo "Applying database migrations..."

# Try to apply migrations normally first
python manage.py migrate --noinput > /tmp/migrate.log 2>&1 || {
    echo "Migration failed, checking if tables already exist..."
    
    # If migration failed due to existing tables, fake the initial migrations
    if grep -q "already exists" /tmp/migrate.log || grep -q "DuplicateTable" /tmp/migrate.log; then
        echo "Tables already exist, faking initial migrations..."
        set +e  # Temporarily disable exit on error
        python manage.py migrate customers 0001 --fake --noinput || true
        python manage.py migrate projects 0001 --fake --noinput || true
        python manage.py migrate timer 0001 --fake --noinput || true
        python manage.py migrate timer 0002 --fake --noinput || true
        python manage.py migrate timer 0003 --fake --noinput || true
        python manage.py migrate timer 0004 --fake --noinput || true
        python manage.py migrate timer 0005 --fake --noinput || true
        python manage.py migrate timer 0006 --fake --noinput || true
        set -e  # Re-enable exit on error
        
        # Now apply remaining migrations
        python manage.py migrate --noinput
    else
        echo "Migration failed for unknown reason:"
        cat /tmp/migrate.log
        exit 1
    fi
}

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
