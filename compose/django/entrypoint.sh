#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

# Wait for PostgreSQL
until python -c "
import psycopg
conn = psycopg.connect('${DATABASE_URL}')
conn.close()
" 2>/dev/null; do
  echo "Waiting for PostgreSQL..."
  sleep 1
done

echo "PostgreSQL is ready."

# Run migrations
python manage.py migrate --noinput

exec "$@"
