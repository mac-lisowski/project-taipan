# Current state

- Branch: `refactor/arch-deepening` at `da81198` (local only, not pushed).
  Three architecture candidates done here: KV collapse (16f52a9), Config
  shrink (da81198), login handshake (uncommitted, review-validated twice:
  code-review + test-smell then scope + live run, all clean).
- Live coverage: full workspace 311 passed, ZERO skips with token.
  New `apps/api/tests/test_kvstore_live.py` (6 tests) drives RedisKVStore
  against real Redis: live Lua CAS win/lose, EX TTL presence, wire keys,
  two namespaces on one client. Skips when Redis unreachable (live_only;
  the marker must be applied to every test - an unapplied marker was the
  bug this file shipped with and fixed). RedisError (not OSError) is the
  catch for redis-py connect failures.
- Tickets 01 AND 02 of login-handshake are done but UNCOMMITTED on this
  branch: new `apps/api/src/api/auth_flow.py` (`InvalidCredentials`,
  `issue`, `login`) plus `apps/api/tests/test_auth_flow.py` (7 seam
  tests, red first, all gates green). Both routers now delegate:
  auth login wraps `auth_flow.login` with `InvalidCredentials` -> 401
  ("invalid email or password", byte-identical); setup terminal lines
  call `auth_flow.issue`. Diff touches only the two router files on
  top of ticket 01; all pin tests pass unmodified (28 targeted; full
  apps/api 236 passed, 2 Infisical-live skips without token).
  Reports next to the ticket files; code-review/stamp boxes open
  until the commit pass.
- Live tests: full workspace 298 passed, ZERO skips. API_INFISICAL_TOKEN
  was minted via the updated recipe (persistent memory
  infisical-token-minting); token at /tmp/api_infisical_token, 7-day TTL.
  The 9 formerly-skipped Infisical-live tests (7 KMS + 2 field_crypto)
  run and pass; no live bugs found.
- Config shape now: `get_config()` returns one frozen `Config` of five
  frozen groups (db, store, crypto, mail, server); `from_env` single
  parse point via `_parse_int`/`_parse_float`; uncached; validation
  precedence preserved and pinned. Test urls live in
  `api_testsupport` (API_TEST_*), not production config. field_crypto
  re-exports no config constants.
- KV shape now: `api/kvstore.py` owns the KVStore port (required
  namespace, SESSION_KEYS/TOKEN_KEYS, CAS Lua), session_store.py twin
  deleted, tokens/store.py wiring only.
- Architecture candidates done: 1 (KV collapse, Strong), 4 (Config
  shrink), 2 login handshake (ticket 01; ticket 02 pending).
  Remaining from /tmp/architecture-review-20261007-122753.html:
  3 seam discipline (Worth exploring), 5 session resolve once
  (Speculative).
- Next: run code-review + stamp and commit the ticket 01+02 diff;
  or push/PR to dev when asked.
