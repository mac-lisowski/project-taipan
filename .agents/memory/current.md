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
- Review/stamp/gate stack (feat/agent-mode-hooks, committed 6be7994
  + fixes 2562d19, PR #3 to dev): pre-exec.sh blocks git commit
  without a diff-bound marker /tmp/taipan-review-<key>-<hash> written
  by review-stamp.sh; bypass vectors denied; subagent calls exempt.
  code-review skill stamps in step 7 on uncommitted diffs (step 6 =
  test-smell pass; diff = git diff HEAD plus untracked files via
  git diff --no-index). plan skill step 7 runs an adversarial
  plan-review subagent (5 axes, BLOCKER/WARNING + file:line, max 2
  rounds). commit-msg stage: check-commit-msg.sh caps every line at
  120, skips #-comments and commit -v scissors. post-write.sh flags
  >3-line comment runs incl /* openers (advisory). pre-write.sh
  protects manifests and gate files, anchored to project root.
- taipan_diff_hash binds HEAD + path/mode/worktree-blob-hash sorted
  (symlinks bind link target) + stale-index cached diffs. git add on
  fully-unstaged work keeps a stamp; partial-staging, content/mode
  edits, or HEAD moves invalidate. External review fixes applied:
  HEAD+mode binding, untracked files in review diff. Exec-side write
  deterrent was tried and REMOVED (lockout, see
  learnings/hook-editing-lockout.md).
- Third review pass on PR #3 (committed 7922d77, needs force-push):
  pre-write.sh traversal bypass fixed (/./ squeeze rewrote ../
  paths; pwd -P canonicalizes alone); pre-exec.sh matches a
  whitespace-flattened copy, denies foreign (-C/--git-dir) commits,
  second commits after separators, and GIT_CONFIG_KEY_n hooksPath
  pairs; stop-nudge.sh gains the script-location root tier and
  literal grep; comment-run counting starts after line 10 (boundary
  runs now flag); taipan_timeout degrades to unbounded without GNU
  timeout (stock macOS); em-dash hook entry is portable sed -i.bak
  (config file excluded from its own gate). Batteries: 23+13+5
  cases green, bash -n clean.
- README image/docs updated: optimized repository image is WebP; prerequisites and Infisical setup documented with provider-neutral production secret guidance.
- Pending: nothing on gates; docs reviewed (no exemption).
- Next step: auth/session layer (FastAPI owns sessions in Redis via
  API_REDIS_URL), src/proxy.ts auth gate once auth endpoints exist
- Blockers: host port 5432 taken by python-playground-db-1; root
  docker-compose.yaml db cannot publish while it runs
