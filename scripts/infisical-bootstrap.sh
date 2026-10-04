#!/usr/bin/env bash
# One-shot Infisical bootstrap. Creates the admin user, the org, and
# an instance-admin machine identity via POST /api/v1/admin/bootstrap.
# Prints the identity token - store it as API_INFISICAL_TOKEN (dev)
# or a Railway variable (prod). Idempotent: exits clean when the
# instance is already initialized.
#
# Env overrides:
#   INFISICAL_URL            default http://localhost:8080
#   INFISICAL_ADMIN_EMAIL    default admin@taipan.local
#   INFISICAL_ADMIN_PASSWORD default taipan-admin
#   INFISICAL_ADMIN_ORG      default taipan
#   INFISICAL_WAIT_RETRIES   default 30 (2s apart)
set -euo pipefail

url=${INFISICAL_URL:-http://localhost:8080}
email=${INFISICAL_ADMIN_EMAIL:-admin@taipan.local}
password=${INFISICAL_ADMIN_PASSWORD:-taipan-admin}
org=${INFISICAL_ADMIN_ORG:-taipan}
retries=${INFISICAL_WAIT_RETRIES:-30}

up=0
for i in $(seq 1 "$retries"); do
  if curl -fsS -o /dev/null "$url/api/status" 2>/dev/null; then
    up=1
    break
  fi
  sleep 2
done
[ "$up" = 1 ] || { echo "infisical not reachable at $url" >&2; exit 1; }

payload=$(printf '{"email":"%s","password":"%s","organization":"%s"}' \
  "$email" "$password" "$org")
if ! resp=$(curl -sS -w $'\n%{http_code}' -X POST "$url/api/v1/admin/bootstrap" \
  -H 'Content-Type: application/json' -d "$payload"); then
  echo "bootstrap request failed (transport error)" >&2
  exit 1
fi
code=${resp##*$'\n'}
body=${resp%$'\n'*}

if [ "$code" -ge 200 ] && [ "$code" -lt 300 ]; then
  echo "bootstrapped: admin=$email org=$org"
  token=$(printf '%s' "$body" | python3 -c '
import json, sys
d = json.load(sys.stdin)
cur = d
for k in ("identity", "credentials", "token"):
    cur = cur.get(k, {}) if isinstance(cur, dict) else {}
print(cur if isinstance(cur, str) else "")
' 2>/dev/null || true)
  if [ -z "$token" ]; then
    token=$(printf '%s' "$body" | sed -n 's/.*"token":"\([^"]*\)".*/\1/p' | head -1)
  fi
  if [ -n "$token" ]; then
    echo "machine identity token (store as API_INFISICAL_TOKEN):"
    echo "$token"
  else
    echo "token not found in response; full body:"
    printf '%s\n' "$body"
  fi
  exit 0
fi

if printf '%s' "$body" | grep -qiE 'already|initialized|exist'; then
  echo "instance already bootstrapped - nothing to do"
  exit 0
fi

echo "bootstrap failed (HTTP $code):" >&2
printf '%s\n' "$body" >&2
exit 1
