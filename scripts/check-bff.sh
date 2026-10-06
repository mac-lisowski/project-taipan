#!/usr/bin/env bash
# BFF boundary checks for apps/web. The browser must never reach
# FastAPI directly: all API traffic goes through the catch-all
# handler in apps/web/src/app/api/. Enforced by pre-commit and CI.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

fail=0
report() { echo "bff-boundary: $1"; fail=1; }

# git grep sees only the index; untracked files are scanned on disk so a
# bypass in a new file cannot slip through a local run.
untracked=$(git ls-files --others --exclude-standard -- apps/web || true)
scan() {
  git grep -nE "$1" -- apps/web 2>/dev/null || true
  if [ -n "$untracked" ]; then
    echo "$untracked" | tr '\n' '\0' | xargs -0 grep -nE "$1" 2>/dev/null || true
  fi
}

# Only real env files are exempt: basenames .env, .env.<x>, <x>.env.
# A source file like foo.env.ts is not exempt.
envline='/(\.env(\.[^/:]*)?|[^/]*\.env):'

# The upstream URL may only be referenced inside the proxy handler.
# Scope is all of apps/web: a rewrite in next.config.ts or a server
# file outside src/ would bypass the boundary just the same.
out=$(scan 'API_INTERNAL_URL' \
  | grep -vE '(src/app/api/|\.md:|Dockerfile)' \
  | grep -vE "$envline" || true)
[ -n "$out" ] && report "API_INTERNAL_URL used outside src/app/api/: $out"

# Any process.env read whose name suggests an upstream address is a
# violation outside the proxy handler, whatever the var is called.
out=$(scan 'process\.env(\.|\[.)[A-Z0-9_]*(URL|URI|ORIGIN|HOST|ENDPOINT|INTERNAL)' \
  | grep -vE '(src/app/api/|\.md:|Dockerfile)' \
  | grep -vE "$envline" || true)
[ -n "$out" ] && report "upstream-address env read outside src/app/api/: $out"

# No NEXT_PUBLIC_* variable may carry the API/backend URL. If the
# browser can read it, the BFF boundary is broken.
out=$(scan 'NEXT_PUBLIC_[A-Z0-9_]*(URL|URI|ORIGIN|HOST|ENDPOINT|API|BACKEND|INTERNAL)' \
  | grep -vE "$envline" || true)
[ -n "$out" ] && report "backend URL in a public env var: $out"

# No backend port reference outside the proxy handler.
out=$(scan ':8000' \
  | grep -vE '(src/app/api/|\.md:|Dockerfile)' \
  | grep -vE "$envline" || true)
[ -n "$out" ] && report "hardcoded backend port outside src/app/api/: $out"

# The proxy layer is server code. A client directive here is a bug.
out=$(scan 'use client' | grep -E '^apps/web/src/app/api' || true)
[ -n "$out" ] && report "'use client' inside the BFF proxy dir: $out"

exit "$fail"
