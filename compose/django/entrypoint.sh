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

# Only the web container runs migrations. Workers wait for them to complete.
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  echo "Running migrations..."
  python manage.py migrate --noinput
  echo "Migrations complete."
else
  # Wait for migrations to be applied (check for a known table)
  echo "Waiting for migrations to complete..."
  until python -c "
import psycopg
conn = psycopg.connect('${DATABASE_URL}')
cur = conn.cursor()
cur.execute(\"SELECT 1 FROM django_celery_beat_crontabschedule LIMIT 1\")
conn.close()
" 2>/dev/null; do
    sleep 2
  done
  echo "Migrations verified."
fi

exec "$@"
