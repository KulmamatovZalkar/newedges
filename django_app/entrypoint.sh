#!/bin/bash
set -e

# Marker file to track first run (stored in persistent volume)
FIRST_RUN_MARKER="/app/.data/.first_run_complete"

echo "========================================"
echo "Starting Django application..."
echo "========================================"

# Wait for database to be ready
echo "Waiting for database..."
max_retries=30
retry=0
while ! python -c "
import os
import psycopg2
url = os.environ.get('DATABASE_URL', '')
url = url.replace('postgres://', '').replace('postgresql://', '')
auth_host, database = url.rsplit('/', 1)
auth, host_port = auth_host.rsplit('@', 1)
user, password = auth.split(':')
host, port = host_port.split(':') if ':' in host_port else (host_port, '5432')
psycopg2.connect(host=host, port=port, database=database, user=user, password=password)
print('Connected!')
" 2>/dev/null; do
    retry=$((retry + 1))
    if [ $retry -ge $max_retries ]; then
        echo "Failed to connect to database after $max_retries attempts"
        exit 1
    fi
    echo "Database not ready (attempt $retry/$max_retries), waiting..."
    sleep 2
done
echo "Database is ready!"

# Run migrations (always)
echo "Running migrations..."
python manage.py migrate --noinput

# Collect static files (always)
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear 2>/dev/null || true

# First run setup (only once)
if [ ! -f "$FIRST_RUN_MARKER" ]; then
    echo "========================================"
    echo "First run detected. Running initial setup..."
    echo "========================================"
    
    # Create superuser from environment variables
    echo "Creating superuser..."
    if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
        python manage.py createsuperuser --noinput 2>/dev/null && echo "Superuser created: $DJANGO_SUPERUSER_USERNAME" || echo "Superuser already exists"
    else
        echo "WARNING: DJANGO_SUPERUSER_USERNAME or DJANGO_SUPERUSER_PASSWORD not set!"
    fi
    
    # Load initial fixtures
    echo "Loading initial data..."
    python manage.py loaddata initial_questions 2>/dev/null && echo "Fixtures loaded successfully" || echo "Fixtures already loaded or not found"
    
    # Create marker file
    mkdir -p "$(dirname "$FIRST_RUN_MARKER")"
    touch "$FIRST_RUN_MARKER"
    echo "========================================"
    echo "First run setup complete!"
    echo "========================================"
else
    echo "Not first run, skipping initial setup."
fi

# Start Gunicorn
echo "Starting Gunicorn on port 8000..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8074 \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
