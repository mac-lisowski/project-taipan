# apps/api rules

Applies inside `apps/api/` in addition to the root `AGENTS.md`.

## Database

- Postgres + pgvector runs on `localhost:5432` via
  `docker compose up -d` on the host, or as the `db` service in the
  devcontainer. The app reads `API_DATABASE_URL`; tests skip when
  Postgres is down.
- Migrations are Alembic, driven by the `db-*` scripts in
  `apps/api/pyproject.toml`.
- After `uv run db-revision -m "msg"`, always review the generated
  file in `alembic/versions/`. Autogenerate misses some changes.
- Never edit a migration that has been applied. Create a new one.
- Run `uv run db-upgrade` before api tests.

## Tests

- `pytest` in this app talks to a real `app_test` Postgres
  database. Tests skip when Postgres is down.
- Connection strings come from `API_TEST_ADMIN_URL` and `API_TEST_URL`
  env vars (localhost defaults; the devcontainer points them at `db`).
- The test DB recreates `vector` extension and tables per session.

## Env

- Local overrides go in `apps/api/.env` (gitignored).
- `apps/api/.env.example` documents the variables.
- Run with overrides: `uv run --env-file apps/api/.env api`.

## Extensibility (Pattern A)

- Core models (such as `User`) contain only identity and credential fields.
- Never add feature-specific columns directly to core models.
- Create feature models in extension tables referencing the entity id.
