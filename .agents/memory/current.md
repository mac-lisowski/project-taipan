# Current state

- Last updated: 2026-10-04
- Done: apps/web shipped via PR #1 (merged to dev). Next.js 16 BFF
  verified e2e and in CI; standalone Dockerfile; strict tsconfig +
  eslint. FastAPI mounted under /api prefix; tests pass (7/7).
  Redis in both compose files; API_REDIS_URL registered.
- Gates live: check-file-size.sh (300 LOC) + check-bff.sh in
  pre-commit and CI lint; pnpm lint + next typegen + tsc on
  pre-push; test-web CI job (lint, typecheck, build, docker build)
  green after pnpm ordering + typegen fixes.
- Next step: auth/session layer (FastAPI owns sessions in Redis via
  API_REDIS_URL), src/proxy.ts auth gate once auth endpoints exist
- Blockers: host port 5432 taken by python-playground-db-1; root
  docker-compose.yaml db cannot publish while it runs
