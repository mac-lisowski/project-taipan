# Current state

- Last updated: 2026-10-05
- Active: branch feat/web-dither-landing (uncommitted). Ported the
  mivia-monorepo LandingDither WebGL canvas to
  apps/web/src/components/dither-background.tsx - grayscale, fixed
  full-viewport, dark-only theme, "project taipan" box on home page.
  Kept field variant only (dropped motifs, containment, scroll drive,
  pulse event) to fit the 300 LOC gate (298 lines). Lint + tsc clean.
  User plans more apps/web updates on this branch.
- PR #9 open: feat/encryption-seam-adr -> dev (field-encryption
  capability, commit 79358e2). ADR-0001 accepted + amended.
  Encryption-seam + field-encryption specs marked implemented.
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
  Seams confirmed by user. Next step: to-tickets, then implement.
- When PR #9 merges: delete .scratch/encryption-seam/prototype.py
  (gitignored scratch) and mark spec statuses with the PR number.
- Remaining unimplemented specs: users-slice, field-encryption-
  hardening. First real encrypted model field after hardening (one
  mapped_column(EncryptedString) line).
- Token for live runs: mint via recipe in memory
  infisical-token-minting.md; /tmp/taipan-infisical-kms-notes/token.md
  (ephemeral) has a valid one.
- Open PRs: #2 (dev -> main), #9 (feat/encryption-seam-adr -> dev).
