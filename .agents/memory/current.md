# Current state

- Last updated: 2026-10-05
- Branch feat/web-dither-landing is clean: dither-background.tsx is
  NOT in the tree. The 298-line WebGL port recorded earlier never
  landed or was reverted; treat it as lost work, not stash.
- Merged into dev: PR #9 field-encryption capability (c652d13) and
  PR #10 web landing/auth/docs (89cfd66). ADR-0001 accepted +
  amended. Encryption-seam + field-encryption specs implemented.
- Shipped in the PR: packages/crypto (envelope grammar, DekManager
  adopt-on-conflict + tenant single-flight, FieldCrypto, CryptoError
  6 codes, context), PostgresDekStore (tenant_deks, alembic
  a3f8c2d91b47), two-tier DEK cache (60s L1 + Redis L2, warm op 47us
  -> 2us, API_DEK_CACHE_L1_TTL), composition root, EncryptedString
  TypeDecorator + lifespan wiring. 56 passed / 0 skipped live.
- Reviews: three full rounds (standards, spec, PG design) clean; the
  round-2 catch was ORM/migration type drift (model now Text +
  timestamptz, catalog-verified on both paths).
- New spec docs/specs/field-encryption-hardening/ (spec.md + html):
  Cipher-port circuit breaker (kms_unavailable, threshold 3 /
  cooldown 30s env), apps/api test-helper dedup, public accessors
  (FieldCrypto.cipher/store/cache, TwoTierDekCache.local/remote).
  Seams confirmed by user. Tickets written: issues/01-05. 01
  done, merged to feat/field-encryption-hardening; 02
  (public accessors) and 05 (kms tests move) done on the
  same branch. 03 (breaker wiring) and 04 (helper dedup)
  done too. Hardening spec implemented. Landed as d0512c3
  (commit-all: hardening 03/04 + CI jobs + tenant-scope
  rewrite + Pattern A track). Next: tightening needs
  to-tickets.
- Known gap: breaker singleton-ness unenforced. Story 4
  (one breaker per process) holds only because the lifespan
  calls the builder once; a second build_field_crypto caller
  would fork breaker state. No test pins it.
- Open decision: Pattern A rule 14 vs users.tenant_id in the
  tenant-scope spec. Recommendation given (keep column:
  tenancy is identity infrastructure, not feature data).
  User has not ruled yet. Foreign entity spec route paths
  fixed to /api prefix, uncommitted.
- Post-#9 cleanup done: .scratch/encryption-seam/prototype.py
  deleted, implemented spec statuses carry PR numbers.
- Architecture review run 2026-10-05; report at
  /tmp/architecture-review-20261005-210214.html (ephemeral). Six new
  specs written, all "not implemented": request-tenant-scope (top
  pick - nothing sets tenant_scope in prod; rewritten 2026-10-05:
  tenants table + session-cookie auth + middleware, env-tenant
  draft deleted per user; lifespan check + before_flush guard kept),
  crypto-interface-tightening (drop DekCache.put ttl_seconds,
  unexport tenant_ctx/DekManager, serialize enforces UUID key id),
  docs-url-policy (docHref/assetHref/resolveDocPath in lib/docs;
  fixes verified 404 in docs/learnings/README.md),
  unreached-ui-cleanup (delete release-grid/live-stats/chrome; keep
  ui primitives), auth-form-module (AuthForm shell + ui Field),
  bff-seam-hardening (property-based check-bff, narrow proxy try,
  PUBLIC_ORIGIN required in prod).
- Amended specs: users-slice (commit boundary moves from
  BaseRepository.add to get_db teardown before repo deletion),
  field-encryption-hardening (packages/kms gets own tests/,
  crypto:dek: prefix pin replaced by accessor assertions).
- Remaining unimplemented specs: users-slice, extensible-user-entity,
  request-tenant-scope,
  crypto-interface-tightening, docs-url-policy, unreached-ui-cleanup,
  auth-form-module, bff-seam-hardening. User order: cleanup/hardening/perf first
  (hardening, tightening, users-slice, ui-cleanup, docs-url,
  auth-form, bff); tenant scope deferred as feature work. First
  real encrypted model field after hardening + tenant scope
  (one mapped_column(EncryptedString)).
- Token for live runs: /tmp/taipan-infisical-kms-notes/token.md
  (ephemeral) holds a valid token plus the curl mint sequence.
  No durable mint recipe exists yet.
- Open PRs: none - all merged, including dev -> main (per user).
- CI fix uncommitted: test-crypto + test-kms jobs in ci.yml, api
  filter covers crypto/kms. Verified fully live: 66 passed,
  0 skipped (DB 15432 + Infisical token + Redis).
