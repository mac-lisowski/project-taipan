# Learnings

## User preferences

- Wants short output, STE100 style, no essays.
- No em dashes.
- New to Python; explain basics briefly, do not over-explain.
- Agent stack notes live in docs/learnings/agents/README.md.
- Wants generic groundwork first (db, repository pattern, structure).
  Evals are later; do not push eval flow before basics exist.
- Deleted packages/support after user rejected domain-named package.

## Gotchas

- Docker daemon is rootless. `rootless` context created and set current;
  system dockerd is off. If docker commands fail, check `docker context ls`.
- Postgres+pgvector runs via `docker compose up -d` (db `app`, port 5432,
  dev creds postgres/postgres). api tests use in-memory SQLite override.
