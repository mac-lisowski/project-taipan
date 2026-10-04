# Current state

- Last updated: 2026-10-04
- Active work: feat/web-bff committed (b4c6091), pushed, PR #1 open
  to dev. CI test-web failed once (pnpm ordering bug); fix applied to
  .github/workflows/ci.yml but UNCOMMITTED - user said do not commit.
  Next: commit+push ci.yml fix, watch CI go green.
- apps/web done: Next.js 16 BFF proxy verified e2e, standalone
  Dockerfile, strict tsconfig+eslint. FastAPI mounted under /api
  prefix; tests updated and pass (7/7).
- Gates live: check-file-size.sh (300 LOC) + check-bff.sh in
  pre-commit and CI lint; pnpm lint+tsc on pre-push; test-web CI job.
- Next step: auth/session layer (FastAPI owns sessions in Redis via
  API_REDIS_URL), src/proxy.ts auth gate once auth endpoints exist
- Blockers: host port 5432 taken by python-playground-db-1; root
  docker-compose.yaml db cannot publish while it runs
