#!/bin/sh
# Container startup: apply migrations, collect static files, then serve.
set -e

echo "== suite-backend starting =="
echo "== Applying database migrations =="
python manage.py migrate --noinput

echo "== Collecting static files =="
python manage.py collectstatic --noinput

echo "== Starting ASGI server (daphne) on 0.0.0.0:${PORT:-8000} =="
# daphne serves HTTP + WebSocket on one port (Channels ASGI app).
exec daphne -b 0.0.0.0 -p "${PORT:-8000}" --access-log - -v 2 core.asgi:application
