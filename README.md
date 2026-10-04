# project-taipan

Learning Python. I know this stack in Node - APIs,
CLIs, agents, databases. The concepts are familiar; this monorepo is
where I learn the Python equivalents: FastAPI, Typer, LangChain etc.

## North star

A production-shaped system, all in Python:

- FastAPI API with Redis-backed sessions
- user panel in `apps/web` (Next.js BFF, SSR, OAuth)
- event-driven communication between services
- CQRS: separate write and read models

A Python monorepo managed with [uv workspaces](https://docs.astral.sh/uv/concepts/workspaces/).
Shared libraries live in `packages/`, runnable applications live in `apps/`.

```
├── pyproject.toml        # workspace root: members, shared dev tools
├── packages/
│   └── core/             # library: core
└── apps/
    ├── cli/              # app: cli (depends on core)
    ├── api/              # app: api (depends on core)
    └── web/              # Next.js frontend, pnpm - not a uv member
```

## Everyday commands

Run from the repo root - one lockfile, one virtualenv for everything:

```bash
uv sync                    # install/update everything into .venv
uv run pytest              # run all tests across all packages
uv run ruff check .        # lint everything

uv add --package core requests   # add a dep to one member
uv add pytest --dev                          # add a shared dev dependency
```

## Run the apps

Each app registers a command in its `pyproject.toml` under `[project.scripts]`.

```bash
uv run cli                 # CLI app -> prints "Hello, world!"
docker compose up -d       # Postgres + pgvector :5432, redis :6379 (needed by api/web)
uv run db-upgrade          # apply migrations
uv run api                 # API app -> FastAPI server on http://127.0.0.1:8000 (docs at /docs)
pnpm -C apps/web install   # one-time: web dependencies
pnpm -C apps/web dev       # Next.js on http://localhost:3000
```

## Database (api)

Postgres 17 + pgvector via docker compose. Schema changes go through Alembic:

```bash
uv run db-revision -m "add orders"   # autogen migration from model changes
uv run db-upgrade                    # apply migrations
uv run db-downgrade                  # roll back one
uv run db-current                    # show applied revision
uv run db-stamp head                 # mark a revision applied without running it
```

Always read the generated file in `apps/api/alembic/versions/` before
applying. Autogen misses renames and data migrations.

API tests run against a real `app_test` database on the docker Postgres
(recreated each run). If Postgres is not up, they skip.

Env vars are registered in `apps/api/.env.example`. Copy to `.env` and run
with `uv run --env-file apps/api/.env api`.

## Frontend (web)

`apps/web` is Next.js acting as the BFF: pages are server-rendered and
a route handler proxies `/api/*` to FastAPI, forwarding the session
cookie. The browser never talks to FastAPI directly.

- `API_INTERNAL_URL` (server-only) lives in `apps/web/.env.example`.
  Copy to `.env.local` for local overrides.
- `apps/web/Dockerfile` builds a standalone production image.
  Build context is the repo root, same as `apps/api/Dockerfile`:
  `scripts/docker-build.sh web`

## Adding a new project

1. Create `packages/<name>/` (library) or `apps/<name>/` (application) with a
   `pyproject.toml` and `src/<import_name>/__init__.py` - copy an existing one.
2. Add it to the root `pyproject.toml` dependencies + `[tool.uv.sources]`
   (`<name> = { workspace = true }`).
3. To depend on another workspace member, do the same in your project's
   `pyproject.toml`.
4. `uv sync`.

## Conventions

- `src/` layout per package (import from `packages/core/src/core`).
- Tests live under `tests/` inside each member that has them.
- Python version pinned in `.python-version`; lockfile is `uv.lock`.
- Source files are capped at 300 lines (`scripts/check-file-size.sh`);
  the web BFF boundary is checked by `scripts/check-bff.sh`; Dockerfile
  COPY sources must resolve at repo root (`scripts/check-docker.sh`,
  since `apps/*/Dockerfile` builds use the root as context). All run
  in pre-commit and CI.
- `pre-commit` runs ruff, an em-dash fixer, and the gate scripts on
  commit; pytest and web lint/typecheck on push.
  Install hooks with `uv run pre-commit install` (commit hook) and
  `uv run pre-commit install --hook-type pre-push` (pytest on push).
  Also run `uv tool install pre-commit` once per machine so the hook's
  PATH fallback works; without it the hook breaks when `.venv` moves.
  Install hooks on the host, not inside the devcontainer - the hook
  stores an absolute `.venv` path that differs between the two.
- Agent hooks enforce the repo rules inside Claude Code, Devin, Grok,
  and ZCode. Scripts live in `.agents/hooks/` - see its README for the
  coverage table and how to test them.
