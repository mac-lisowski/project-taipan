# Current state

- Branch: `feat/api-modularization` at `b40a7a2`, pushed; PR #31 open to
  `dev` (https://github.com/mac-lisowski/project-taipan/pull/31).
- State: API modularization implemented, reviewed, committed. One commit,
  34 files (+1222/−151). Review stamped (2a79f590) after code-review,
  test-smell-review, spec audit, and coverage rounds. Tickets in
  `.scratch/api-modularization/issues/` are local-only (gitignored),
  Status done, boxes ticked, HTML reports written.
- Notable: password policy min length 8 (`credentials/service.py`);
  epoch-based revoke_all (`session-epoch:{user_id}`); verifier slot
  (`api/verifiers.py`); consumed tokens get 60s grace TTL;
  `FakeRedis.eval` CAS stub refuses script drift vs `_CAS_LUA`;
  `wipe_tables` fixture wipes all tables reverse-FK order.
- Tests: apps/api 203 passed, workspace 263 passed, 9 live skips;
  coverage 95% (api). All gates green. `.coverage` now gitignored.
- Architecture review: /tmp/architecture-review-20261007-122753.html;
  top candidate: collapse twin KV store modules (Strong). Not picked yet.
- Next: CI on PR #31; merge (squash, matching prior PRs); flip spec
  Status to implemented after merge per repo convention.
