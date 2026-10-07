# Current state

- Branch: `refactor/arch-deepening` at `da81198` (local only, not pushed).
  Two architecture candidates landed here: KV store collapse (16f52a9) and
  Config interface shrink (da81198, 16 files). Both review-stamped and
  committed; pre-commit gates green. Not on dev yet.
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
  shrink). Remaining from /tmp/architecture-review-20261007-122753.html:
  2 login handshake, 3 seam discipline (both Worth exploring),
  5 session resolve once (Speculative).
- Next: push/PR to dev when asked; or pick the next candidate.
