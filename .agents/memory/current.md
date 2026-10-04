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
- Infisical self-host (feat/infisical, UNCOMMITTED): docker/
  infisical/Dockerfile pins infisical/infisical:v0.165.16 for
  `railway up`; dedicated infisical-db Postgres service in both
  compose files (postgres:17-alpine, creds infisical/infisical, no
  host port, own volume - mirrors cloud shape; stale `infisical`
  db may linger inside shared pg volumes, harmless);
  infisical service in root compose (:8080) + devcontainer compose
  (no host port, API_INFISICAL_URL=http://infisical:8080 on app);
  scripts/infisical-bootstrap.sh does POST /api/v1/admin/bootstrap
  (admin@taipan.local/taipan-admin defaults, idempotent, prints MI
  token); API_INFISICAL_URL/TOKEN in api .env.example; CI deploy gets
  var-guarded RAILWAY_SERVICE_INFISICAL step; test_infisical.py (3
  tests, skip-when-down). Verified: both stacks up, bootstrap+rerun,
  pytest 3/3. check-docker.sh glob now covers apps/* + docker/* +
  .devcontainer Dockerfile* (all root-context builds gated).
- Infisical dev service live on Railway: PR #4 merged; fixed two
  config bugs (SITE_URL lacked https:// -> WebAuthn crash -> 502;
  Postgres moved same-region, migrations 20+min -> 90s). User set up
  admin via web bootstrap; KMS key created via UI; MI `taipan-api`
  with `cryptographic-operator` role + Token Auth. Vars
  AUTH_SECRET/DB_CONNECTION_URI/ENCRYPTION_KEY/REDIS_URL/SITE_URL set;
  api needs API_INFISICAL_URL/TOKEN/KMS_KEY_ID on Railway.
- Branch feat/infisical-kms (uncommitted): spec written at
  docs/specs/infisical-kms/spec.md (packages/kms client + admin
  provisioning + integration tests vs live instance, decided:
  self-provision fixture, encrypt/decrypt+rotate coverage, export
  off). to-spec patched: specs -> docs/specs/<slug>/spec.md;
  to-tickets installed from mattpocock/skills, patched: tickets ->
  .scratch/<slug>/issues/ (.scratch now gitignored); implement-spec +
  code-review de-trackered.
- infisical-kms review fixes (feat/infisical-kms): _request wraps
  httpx2.HTTPError in KmsError (spec story 5, chained via from);
  test_transport_error_raises_kmserror runs everywhere (port 1).
  Test file refactor: skip moved from pytestmark to per-test
  live_only marker so the transport test is never skipped; Keys
  NamedTuple now carries client+project_id+key_a (descriptive names,
  no more per-test InfisicalKms construction); key B created inline
  in test_cross_key_decrypt_fails per ticket 02.
- Pending: merge feat/infisical-kms to dev (tickets 01-03 done,
  memory DoD boxes ticked) (packages/kms, KmsClient
  encrypt/decrypt/rotate, admin create/del project+key, tests in
  apps/api/tests/test_infisical_kms.py, docs/infisical.md,
  .env.example KMS_KEY_ID).
- Next step: auth/session layer (FastAPI owns sessions in Redis via
  API_REDIS_URL), src/proxy.ts auth gate once auth endpoints exist
- Blockers: host port 5432 taken by python-playground-db-1; root
  docker-compose.yaml db cannot publish while it runs
