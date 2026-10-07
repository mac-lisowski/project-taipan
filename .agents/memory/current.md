# Current state

- Branch: `refactor/arch-deepening` cut from dev `02c8f4f`. Old
  `feat/api-modularization` deleted (local + remote); work squash-merged
  via PR #31 (`ee63735`).
- Local tickets + HTML reports for the merged work live in
  `.scratch/api-modularization/issues/` (gitignored).
- Architecture review picked: collapse twin KV store modules (Strong).
  Spec `.scratch/kv-store-collapse/`: tickets 01 (api/kvstore.py +
  test_kvstore.py) and 02 (repoint consumers, delete twins) implemented
  on `refactor/arch-deepening`, uncommitted.
- Two review passes done; 4 findings fixed, still uncommitted: unused
  `runtime_checkable` dropped from the `KVStore` Protocol;
  `test_memory_stores_with_different_namespaces_never_collide` shares one
  backing dict between the stores via the `entries=` constructor arg
  (namespace prefix is the only isolation, re-proven red by dropping
  the prefix, then green); the four non-positive-TTL guards deduplicated
  into module-level `_require_positive_ttl` in kvstore.py; private seams
  made public (`MemoryKVStore.entries` dict, `build_token_store` in
  api/tokens/store.py).
- Twins are gone: `api/session_store.py` and its test deleted;
  `api/tokens/store.py` is wiring only. All consumers use the `KVStore`
  port; wire keys unchanged, no migration needed.
- KV collapse cut the api suite to 211 passed, 2 live skips (down from
  226: the 16 duplicated twin tests were deleted; +1 fixture pin).
  Workspace outside apps/api untouched.
- Shrink-config ticket 03 done (uncommitted): `get_config()` returns
  one frozen `Config` of five frozen groups (`db`, `store`, `crypto`,
  `mail`, `server`; classes `DbConfig`...`ServerConfig` in
  `api/config.py`). `from_env` single parse point; the six hand-rolled
  int/float blocks now go through `_parse_int` (optional `hi` covers
  the port 1..65535 rule) and `_parse_float`; messages byte-identical.
  `get_config()` stays UNCACHED (scratch-url monkeypatch and behavior
  tests rely on re-reads). No new imports in config.py. Callers
  repointed: db.py, db_cli.py (`.db.database_url`), kvstore.py,
  tokens/store.py (`.store.redis_url`), sessions.py
  (`.store.session_ttl_seconds`), field_crypto.py (`.crypto.*` +
  `.store.redis_url`), mail.py (`.mail.*`), main.py `_serve` (host/port
  from `get_config().server`, raw `os.environ` reads gone).
  `test_config.py` rewritten (40 items; 13 invalid-env cases verbatim;
  new pins: five-group field list, equal Configs, no test_* fields,
  2-case multi-invalid precedence pin, one frozen-mutation case per
  group plus the group-slot assert, uncached get_config, config-level
  twin of ticket 02's re-export pin). `test_mail_wiring.py` repointed to
  `cfg.mail.*`; `test_kvstore.py` needed no edit (its builder test
  passes the whole Config, reads no flat field). Red-first proof:
  19 failed / 19 passed on the flat Config before the rewrite.
  Report: `.scratch/shrink-config/issues/03-group-concern-values.html`.
- Shrink-config review pass done; all 5 findings fixed, uncommitted:
  M1 restored the pre-grouping validation order in `from_env` (key id,
  threshold, cooldown, dek ttls, port, session ttl, mail cross-check
  last) after the grouped rewrite had moved the mail check first; the
  2-case precedence pin failed red before the fix. LOW fixes:
  test_url_ownership reload snapshot/restores TEST_ADMIN_URL/TEST_URL
  in a finally; frozen-mutation cases trimmed 14 to 5 (one field per
  group); duplicate re-export pin deleted from test_field_crypto_live.py
  (kept in test_config.py); test_mail_wiring schema check asserts 200
  before the key-not-in-body asserts.
- Tests on the branch now: api suite 229 passed, 2 live skips (240
  before the review fixes: -9 frozen trims, -4 dedup, +2 precedence).
- Tickets 01, 02, 03 all done, uncommitted. 02's deferred
  "Full api suite green" and "Every acceptance criterion checked"
  boxes ticked off ticket 03's green full run. All three tickets keep
  only the code-review/stamp box unticked (orchestrator's pre-commit
  pass).
- Next: review stamp on the whole diff, then commit.
