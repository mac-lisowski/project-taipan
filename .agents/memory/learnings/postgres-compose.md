# Postgres+pgvector via compose; tests need it

Runs via `docker compose up -d` (db `app`, port 5432, dev creds
postgres/postgres). api tests need that Postgres: they create and
wipe an `app_test` database, and skip if Postgres is down.
