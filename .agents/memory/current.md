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
- Tests on the branch: api suite 211 passed, 2 live skips (down from
  226 because the 16 duplicated twin tests were deleted; +1 fixture
  pin). Workspace outside apps/api untouched.
- Next: review stamp on the fixed diff, then commit.
