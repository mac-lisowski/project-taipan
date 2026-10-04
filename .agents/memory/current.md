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
- Test quality gate (committed 7770c19): installed
  `collectiveai-team/botica@test-smell-review` via `npx skills add`.
  Trimmed botica-internal refs (drift: `npx skills update` clobbers).
  Wired: AGENTS.md rule 9, plan skill step 6 + output, implement-spec
  step 4. `uvx falsegreen <files>` is the structural pass.
- Agent mode system (feat/agent-mode-hooks, committed 7e9b63d,
  pushed): agent-mode.sh set|get|clear|list over fixed enum
  (plan implement test review debug docs commit); state file
  /tmp/taipan-mode-<rootkey>; route.sh dispatches to
  hooks.d/<mode>/<event>.sh (advisory nudges, once per mode-set,
  never block, skipped in subagents). Wired into all four tool hooks
  + session-start. AGENTS.md rule 10. post-write.sh also runs
  falsegreen on test files deterministically.
- Second review pass (committed e2d894e): parent hooks resolve root
  env -> script location -> cwd; routes read TAIPAN_TARGET;
  falsegreen-js glob covers colocated *.test.js/.jsx and __tests__/.
- Review/stamp/gate stack (UNCOMMITTED): pre-exec.sh blocks git
  commit without a diff-bound marker /tmp/taipan-review-<key>-<hash>
  written by review-stamp.sh; bypass vectors denied; subagent calls
  exempt. code-review skill stamps in step 7 on uncommitted diffs
  (step 6 = test-smell pass on touched tests). plan skill step 7 runs
  an adversarial plan-review subagent (coverage/grounding/scope/
  feasibility/test-strategy, BLOCKER/WARNING with file:line, max 2
  rounds). commit-msg stage: scripts/check-commit-msg.sh caps every
  line at 120, skips #-comments and commit -v scissors; installed via
  pre-commit install --hook-type commit-msg. post-write.sh flags
  >3-line comment runs incl /* openers (advisory). pre-write.sh
  protects manifests and gate files, anchored to project root.
  Exec-side write deterrent was tried and REMOVED: a syntax bug
  locked out all exec - that file is a loaded gun, see
  learnings/hook-editing-lockout.md.
- Third review pass fixes (UNCOMMITTED): taipan_diff_hash now binds
  worktree blob hashes per changed path, path-sorted, so git add
  does not invalidate a stamp (partial-staging still does); untracked
  file contents are hashed, not just paths. commit-tree/update-ref
  denial moved to the always-on dangerous-command case (was dead code
  standalone). Commit match widened to git -<global-flags>. -n bundle
  check is a per-token loop scoped to the commit args (fixes both the
  missed -sn/-ns bundles and false blocks on neighbouring bash -n).
  dhash empty now blocks instead of failing open. git config
  --get/--list on hooksPath exempted.
- Pending: nothing on gates; docs reviewed (no exemption).
- Next step: auth/session layer (FastAPI owns sessions in Redis via
  API_REDIS_URL), src/proxy.ts auth gate once auth endpoints exist
- Blockers: host port 5432 taken by python-playground-db-1; root
  docker-compose.yaml db cannot publish while it runs
