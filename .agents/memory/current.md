# Current state

- Last updated: 2026-10-05
- On feat/encryption-seam-adr (off dev, commit fdf4f93), everything
  uncommitted, review-stamped: ADR-0001 accepted + amended,
  field-encryption spec (docs/specs/field-encryption/), tickets 01-03.
- New spec written: docs/specs/field-encryption-hardening/ (spec.md
  + spec.html), from the deferred review items: Cipher-port circuit
  breaker (kms_unavailable code, threshold 3 / cooldown 30s env
  config), apps/api test-helper dedup (testsupport module), public
  accessors (FieldCrypto.cipher/store/cache,
  TwoTierDekCache.local/remote). Seams confirmed by user. Not
  ticketed yet; to-tickets when the user says go.
- ALL THREE field-encryption tickets implemented, reviewed (test-smell
  + code-review agents per ticket, findings fixed), and verified live:
  - 01: packages/crypto (envelope grammar, DekManager adopt-on-conflict
    + tenant single-flight, FieldCrypto, CryptoError 5 codes, context).
  - 02: apps/api PostgresDekStore (tenant_deks, alembic a3f8c2d91b47,
    up/down/up verified), RedisDekCache (TTL, degrade), composition
    root build_field_crypto (None when unconfigured).
  - 03: EncryptedString TypeDecorator (pure delegation, flush-time
    tenant read), set_field_crypto registration, lifespan wiring in
    api.main, ORM tests on SQLite + live proof tests.
- Live verification: full suite 55 passed 0 skipped against real
  Postgres (:15432 test DB), Redis (:6379), Infisical (:8080) incl.
  full-chain cold decrypt, rotate-then-unwrap, transport-failure
  mapping. App boots with lifespan (do not touch :8000).
- Whole-scope reviews (perf + smell agents) done 2026-10-05, fixes
  in: two-tier DEK cache (LocalTtlDekCache 60s L1 + Redis L2; warm op
  47us -> 2us, API_DEK_CACHE_L1_TTL), cache=None now means
  unwrap-per-use (null cache, spec-aligned), striped 32-lock pool in
  DekManager, envelope parse speedup (set-subset charset checks),
  NONCE_BYTES + parse exported from crypto, engine rejects resolver +
  default_key_id together, TTL live test asserts redis ttl() instead
  of wall-clock poll, lifespan unregisters on shutdown, stub fixture
  restores prior registration. Deferred: AESGCM-per-tenant instance
  cache (0.6us/op), circuit breaker on cold unwrap (documented in
  spec), test-helper dedup, private-state accessor for wiring test.
- Spec statuses updated: field-encryption = implemented (this
  branch, not merged); encryption-seam = implemented + seam chosen
  line. Remaining unimplemented specs: users-slice,
  field-encryption-hardening (spec docs only, no tickets yet).
- Token for live runs: mint via recipe in memory
  infisical-token-minting.md; /tmp/taipan-infisical-kms-notes/token.md
  (ephemeral) has a valid one.
- Next: user reviews the diff, says commit message preference; then
  commit + PR to dev when asked. First real encrypted model field is
  the follow-up (one mapped_column(EncryptedString) line). users-slice
  still not implemented.
- Prototype in .scratch/encryption-seam/ dies when the spec's PR
  merges.
- Open PR: #2 (dev -> main).
