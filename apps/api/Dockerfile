# Build context is the repo root (api depends on the workspace package core):
#   docker build -f apps/api/Dockerfile -t taipan-api .
# Run (Postgres from docker-compose.yaml on the host):
#   docker run --rm -p 8000:8000 \
#     -e API_DATABASE_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/app \
#     taipan-api
# Migrations inside the image:
#   docker run --rm -e API_DATABASE_URL=... taipan-api db-upgrade
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

# Manifests + lockfile first so this layer caches dependency installs.
COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY apps/cli/pyproject.toml apps/cli/pyproject.toml
COPY packages/core/pyproject.toml packages/core/pyproject.toml
RUN uv sync --frozen --no-dev --package api --no-install-workspace

# Editable installs keep db_cli.py's parents[2] lookup of alembic.ini working.
COPY packages/core packages/core
COPY apps/api apps/api
RUN uv sync --frozen --no-dev --package api

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
