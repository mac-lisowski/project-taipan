#!/usr/bin/env bash
set -euo pipefail

# Run migrations if enabled
if [ "${API_AUTO_MIGRATE:-1}" = "1" ] || [ "${API_AUTO_MIGRATE:-1}" = "true" ]; then
  if [ "$#" -eq 0 ] || [ "$1" = "uvicorn" ] || [ "$1" = "api" ]; then
    db-upgrade
  fi
fi

exec "$@"
