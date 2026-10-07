# Current state

- Branch: `feat/api-modularization` at `bce8a3d` (spec pair committed).
- State: DONE. Workflow run `dwfrun-caf1464d` implemented all 5 tickets
  (tokens, credentials, sessions, users+profiles+setup, thin routers) plus a
  code-review/fix round. All work uncommitted on this branch per user
  instruction; ticket reports at `.scratch/api-modularization/issues/0*.html`.
- Next: user reviews the diff; commit only on explicit ask (review stamp
  flow applies then).
- Follow-up fixes done by agents: password policy is now min length 8
  (`credentials/service.py ensure_acceptable`); many test fixtures moved to
  valid passwords. The revoke-all TTL finding was stale: the refactor already
  uses epoch-based revocation (`session-epoch:{user_id}`, no per-mint
  refresh); only a missing end-to-end regression test was added.
- Second review round (3 agents): architecture clean, code review clean,
  one proven test defect fixed - `wipe_users` fixture renamed `wipe_tables`,
  now wipes all tables in reverse FK order (tenants used to leak and
  test_auth was order-dependent). Tokens: consumed records rewritten with
  60s grace TTL (`CONSUMED_TTL_GRACE_SECONDS`); lazy import moved to top;
  Clock fakes consolidated into `api_testsupport.FakeClock`; 8-char password
  boundary pinned; default-TTL test now two-sided (7 days, from config
  constant).
- Coverage round: 6 untested branches closed with tests only, no src edits.
  Memory + Redis `set_if_unchanged` win/lose and ttl guards now pinned;
  `FakeRedis.eval` runs the CAS script and refuses any other script shape,
  so a Lua edit fails tests instead of drifting. Corrupt token record,
  non-dict session payload, DELETE missing user 404, and
  `tenant_id_for_user` without a tenant row all covered. Red-run proven:
  each CAS loser branch mutation was caught. No src bugs found. Full suite
  203 passed, 2 skipped; ruff, falsegreen, file-size gates green.
- Third review round (5 agents): code-review Standards axis 0 hard
  violations / 6 judgement smells (worst: tokens/ 236 LOC with no
  production caller yet - by design, spec orders tokens before flows);
  Spec axis all 5 ticket ACs met; test-smell 118 tests, 0 findings;
  coverage 95% apps/api. Architecture report:
  /tmp/architecture-review-20261007-122753.html (top candidate: collapse
  twin KV store modules, Strong). Awaiting user pick + commit timing.
- Final state: full workspace suite 263 passed, 9 skipped (7 KMS live +
  2 api Infisical-live); ruff + file-size gates green. No stamp yet.
- Next: user decides on architecture candidates; commit flow =
  code-review skill clean + review-stamp.sh, only on explicit ask.
