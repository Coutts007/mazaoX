#!/bin/sh
set -e
# Migrations are opt-in so they are never applied by surprise (set RUN_MIGRATIONS=true in compose for dev).
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  python manage.py migrate --noinput
fi
exec "$@"
