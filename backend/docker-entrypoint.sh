#!/bin/sh
set -e
# Run DB migrations before the app (no-op when already at head).
# Acceptable for single-instance staging; use a one-off job for multi-replica production.
alembic upgrade head

if [ "$#" -eq 0 ]; then
  exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
else
  exec "$@"
fi
