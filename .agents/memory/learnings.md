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
- uv workspace `members = ["apps/*"]` glob matches apps/web (no
  pyproject.toml). `uv sync --frozen` passes but `uv run` fails:
  "workspace member is missing a pyproject.toml". Fix is
  `exclude = ["apps/web"]` under `[tool.uv.workspace]`.
- GitHub Actions: `setup-node` with `cache: pnpm` runs pnpm during
  its own step to resolve cache paths, so pnpm must already exist.
  `corepack enable` in a later step is too late. Use
  `pnpm/action-setup` BEFORE `setup-node`, and set its
  `package_json_file: apps/web/package.json` - it defaults to the
  repo-root package.json which does not exist here.
- Next 16 emits `LayoutProps`/`PageProps` global types into
  `.next/types` only. On a clean checkout `tsc --noEmit` fails
  (TS2304). Run `pnpm exec next typegen` before `tsc`; it is fast.
- Verify CI jobs locally with `act` before claiming they pass:
  `DOCKER_HOST=unix:///run/user/1000/docker.sock act push -j <job>
  -P ubuntu-latest=catthehacker/ubuntu:act-24.04
  --container-daemon-socket /run/user/1000/docker.sock`.
