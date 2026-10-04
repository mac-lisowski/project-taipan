#!/usr/bin/env bash
# BFF boundary checks for apps/web. The browser must never reach
# FastAPI directly: all API traffic goes through the catch-all
# handler in apps/web/src/app/api/. Enforced by pre-commit and CI.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

fail=0
report() { echo "bff-boundary: $1"; fail=1; }

# The upstream URL may only be referenced inside the proxy handler.
out=$(git grep -l 'API_INTERNAL_URL' -- 'apps/web/src' 2>/dev/null \
  | grep -v '^apps/web/src/app/api/' || true)
[ -n "$out" ] && report "API_INTERNAL_URL used outside src/app/api/: $out"

# No NEXT_PUBLIC_* variable may carry the API/backend URL. If the
# browser can read it, the BFF boundary is broken.
out=$(git grep -nE 'NEXT_PUBLIC_[A-Z0-9_]*(API|BACKEND|INTERNAL)' -- apps/web 2>/dev/null || true)
[ -n "$out" ] && report "backend URL in a public env var: $out"

# No hardcoded backend origin outside the proxy handler.
out=$(git grep -nE '(localhost|127\.0\.0\.1):8000' -- 'apps/web/src' 2>/dev/null \
  | grep -v 'src/app/api/' || true)
[ -n "$out" ] && report "hardcoded backend origin outside src/app/api/: $out"
out=$(git grep -n '8000' -- 'apps/web/next.config.ts' 2>/dev/null || true)
[ -n "$out" ] && report "backend origin in next.config.ts: $out"

# The proxy layer is server code. A client directive here is a bug.
out=$(git grep -ln 'use client' -- 'apps/web/src/app/api' 2>/dev/null || true)
[ -n "$out" ] && report "'use client' inside the BFF proxy dir: $out"

exit "$fail"
