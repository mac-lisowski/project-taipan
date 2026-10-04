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
