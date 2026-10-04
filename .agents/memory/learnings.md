# Learnings

## User preferences

- Wants short output, STE100 style, no essays.
- No em dashes.
- New to Python; explain basics briefly, do not over-explain.
- Agent stack notes live in docs/learnings/agents/README.md.
- Wants generic groundwork first (db, repository pattern, structure).
  Evals are later; do not push eval flow before basics exist.
- Wants domain-named packages where they fit. Packages should be
  shareable and reusable, not app-specific.

## Gotchas

- Docker daemon is rootless. `rootless` context created and set current;
  system dockerd is off. If docker commands fail, check `docker context ls`.
- Postgres+pgvector runs via `docker compose up -d` (db `app`, port 5432,
  dev creds postgres/postgres). api tests need that Postgres: they create
  and wipe an `app_test` database, and skip if Postgres is down.
- Dev dep is `httpx2`, an httpx fork. starlette's TestClient imports it as
  `httpx` automatically; plain `import httpx` fails. Not a typo.
- Rootless Docker uid mapping: host uid 1000 = container uid 0.
  Bind mounts look root-owned inside. Non-root container users cannot
  write them. Devcontainers on this host must run as root.
- `pre-commit install` bakes an absolute `INSTALL_PYTHON` into
  `.git/hooks/*`. Host and devcontainer share `.git` but use different
  `.venv` paths (`/home/mac/...` vs `/workspaces/...`), so whichever
  side installs last breaks the other (`pre-commit not found`). Fix:
  both sides need `pre-commit` on PATH for the hook's `command -v`
  fallback - host: `uv tool install pre-commit`; container: symlink
  `.venv/bin/pre-commit` to `/usr/local/bin` (in postCreateCommand).
