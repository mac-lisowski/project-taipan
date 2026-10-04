# project-taipan

A Python monorepo managed with [uv workspaces](https://docs.astral.sh/uv/concepts/workspaces/).
Shared libraries live in `packages/`, runnable applications live in `apps/`.

```
├── pyproject.toml        # workspace root: members, shared dev tools
├── packages/
│   └── core/             # library: core
└── apps/
    ├── cli/              # app: cli (depends on core)
    └── api/              # app: api (depends on core)
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
docker compose up -d       # Postgres + pgvector on localhost:5432 (needed by api)
uv run db-upgrade          # apply migrations
uv run api                 # API app -> FastAPI server on http://127.0.0.1:8000 (docs at /docs)
```

## Database (api)

Postgres 17 + pgvector via docker compose. Schema changes go through Alembic:

```bash
uv run db-revision -m "add orders"   # autogen migration from model changes
uv run db-upgrade                    # apply migrations
uv run db-downgrade                  # roll back one
```

Always read the generated file in `apps/api/alembic/versions/` before
applying. Autogen misses renames and data migrations.

API tests run against a real `app_test` database on the docker Postgres
(recreated each run). If Postgres is not up, they skip.

Env vars are registered in `apps/api/.env.example`. Copy to `.env` and run
with `uv run --env-file apps/api/.env api`.

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
- Tests live in each package under `tests/`.
- Python version pinned in `.python-version`; lockfile is `uv.lock`.
