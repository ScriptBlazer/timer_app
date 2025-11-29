#!/bin/bash

# Timer Tracking App - Start Script

echo "Starting Timer Tracking App..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run migrations
echo "Running database migrations..."
python manage.py migrate

# Start the server
echo ""
echo "================================================"
echo "Starting development server..."
echo "Access the app at: http://127.0.0.1:8000/"
echo "Press Ctrl+C to stop the server"
echo "================================================"
echo ""
export DJANGO_SETTINGS_MODULE=config.settings
python manage.py runserver

