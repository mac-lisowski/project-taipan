#!/usr/bin/env bash
set -euo pipefail

# Run migrations if enabled
if [ "${API_AUTO_MIGRATE:-1}" = "1" ] || [ "${API_AUTO_MIGRATE:-1}" = "true" ]; then
  if [ "$#" -eq 0 ] || [ "$1" = "uvicorn" ] || [ "$1" = "api" ]; then
    db-upgrade
  fi
fi

# Respect platform PORT when set (e.g. Railway internal routing)
if [ "${1:-}" = "uvicorn" ] && [ -n "${PORT:-}" ]; then
  exec uvicorn api.main:app --host "${HOST:-0.0.0.0}" --port "$PORT"
fi

exec "$@"
