# Current state

- Last updated: 2026-10-04
- Active work: apps/web on branch feat/web-bff (uncommitted). Next.js 16
  BFF verified e2e: :3000/api/users -> FastAPI /api/users (FastAPI now
  mounts under /api prefix). pnpm, standalone Dockerfile, image serves
  200. Redis in both compose files. Devcontainer: node feature, :3000.
- Gates added: scripts/check-file-size.sh (300 LOC), scripts/check-bff.sh
  (BFF boundary). Both in pre-commit + CI lint job. web-checks
  (pnpm lint + tsc) on pre-push; test-web job in CI incl. docker build.
  tsconfig strict flags + eslint no-explicit-any etc. post-write.sh
  warns on BFF violations and over-long files.
- Known: `uv run` failed until `exclude = ["apps/web"]` was added to
  tool.uv.workspace (members glob `apps/*` matched web).
- Next step: auth/session layer (FastAPI owns sessions in Redis),
  src/proxy.ts auth gate once auth endpoints exist
- Blockers: host port 5432 taken by python-playground-db-1; root
  docker-compose.yaml db cannot publish while it runs
