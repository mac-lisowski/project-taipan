# Current state

- Last updated: 2026-10-04
- Done: apps/web shipped via PR #1 (merged to dev). Next.js 16 BFF
  verified e2e and in CI; standalone Dockerfile; strict tsconfig +
  eslint. FastAPI mounted under /api prefix; tests pass (7/7).
  Redis in both compose files; API_REDIS_URL registered.
- Gates live: check-file-size.sh (300 LOC) + check-bff.sh +
  check-docker.sh (Dockerfile COPY sources resolve at repo root) in
  pre-commit and CI lint; pnpm lint + next typegen + tsc on
  pre-push; test-web CI job builds web image with root context.
- Docker context fix + gate hardening (staged on dev, UNCOMMITTED):
  root-context Dockerfiles, scripts/docker-build.sh as canonical
  build cmd, check-docker.sh hardened (ADD, case, continuations,
  JSON-form, pnpm -C flag), check-bff.sh widened to all apps/web,
  .dockerignore nested .env exclusion verified, api image runs
  non-root, CI smoke-runs both images, compose files validated in
  lint job, push:[dev] coverage. act: lint + test-web green.
  route.ts hardened live-tested: spoofed fwd headers stripped,
  timeout 502, streamed bodies, Location/cookie rewrite, path
  segment 400s, outputFileTracingRoot pinned.
- PR #2 dev->main open. Once staged docker work is committed, it
  lands on dev.
- Railway deploys moved to CI: both services disconnected from
  the GitHub repo source (no Deployment records, no check runs).
  New `deploy` job in ci.yml runs `railway up --service <name>
  --ci` for web then api after `ci-done` on push to dev.
  Secrets RAILWAY_TOKEN + RAILWAY_PROJECT_ID and vars
  RAILWAY_ENVIRONMENT, RAILWAY_SERVICE_WEB, RAILWAY_SERVICE_API
  live on GitHub env `project-taipan / dev` (branch policy: dev);
  deploy job declares environment: so they resolve.
- Test quality gate (UNCOMMITTED): installed
  `collectiveai-team/botica@test-smell-review` via `npx skills add`.
  Trimmed botica-internal refs (drift: `npx skills update` clobbers).
  Wired: AGENTS.md rule 9, plan skill step 6 + output, implement-spec
  step 4. `uvx falsegreen <files>` is the structural pass.
- Next step: auth/session layer (FastAPI owns sessions in Redis via
  API_REDIS_URL), src/proxy.ts auth gate once auth endpoints exist
- Blockers: host port 5432 taken by python-playground-db-1; root
  docker-compose.yaml db cannot publish while it runs
