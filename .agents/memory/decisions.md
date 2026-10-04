# Decisions

- Prefer domain-named packages where they fit. Design packages to be
  shareable and reusable, not app-specific.
- Dev dep is `httpx2` (httpx fork), not `httpx`. starlette TestClient
  supports it natively.
- Devcontainer is compose-based and self-contained (app + db + dind).
  Does not merge root docker-compose.yaml; its 5432 publish would
  collide on the host.
- Devcontainer runs as root. Rootless Docker maps host uid to
  container 0, so a normal user cannot write the bind mount.
- testcontainers get a sibling `dind` service (privileged,
  DOCKER_HOST=tcp://dind:2375) instead of the host socket. Keeps test
  containers off the host daemon and avoids rootless socket quirks.
- Test DB URLs moved to env vars API_TEST_ADMIN_URL/API_TEST_URL so
  conftest works on host (localhost) and in devcontainer (db).
- Agent hook scripts live once in `.agents/hooks/` (tool-agnostic
  bash+jq). `.claude/settings.json` is the single manifest: Claude
  reads it natively, Devin and Grok via their `.claude` compat layers.
  No `.devin/hooks.v1.json` - Devin reads both and hooks would fire
  twice. ZCode gets its own `.zcode/config.json` (hooks.enabled).
- Web is Next.js BFF (Option B.1): browser only reaches Next, the
  catch-all in `src/app/api/[...path]/route.ts` forwards to FastAPI.
  FastAPI owns sessions + Redis; web has no REDIS_URL, only
  API_INTERNAL_URL (server-only, never NEXT_PUBLIC_).
- FastAPI mounts all routers under `prefix="/api"` so the BFF proxy
  is a dumb 1:1 forwarder with no path rewriting.
- Hard file cap is 300 LOC (scripts/check-file-size.sh) and the BFF
  boundary is scripts/check-bff.sh; both run in pre-commit and the
  CI lint job. Exemptions only in the scripts, with a reason.
