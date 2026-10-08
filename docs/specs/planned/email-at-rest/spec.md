# Spec: Email at rest encryption

Status: planned.

Seam: users.email becomes the first EncryptedString column. A blind
index column owns lookup and uniqueness. One re-scope helper owns
reads that need plaintext. Email delivery tables keep plaintext
addresses.

## Problem Statement

User emails sit in plaintext in the users table. A database read or
backup leaks every address. The crypto capability exists (ADR-0001,
packages/crypto) but no column uses it yet. Login, magic link, and
password reset all find users by exact email match, and the email
column carries a unique index. Randomized ciphertext cannot serve
either. Lookup and uniqueness need their own design.

## Solution

Keep users.email as encrypted ciphertext. Add users.email_hash, an
HMAC blind index over the normalized address, and move the unique
index to it. Lookups hash first, then match. Reads that need
plaintext re-scope to the row owner's tenant and decrypt there. The
data conversion rides the existing deploy path.

## User Stories

1. As a user, I want my email encrypted at rest, so that a database
   leak does not expose it.
2. As a user, I want login, magic link, and reset to keep working,
   so that the change is invisible to me.
3. As an operator, I want the upgrade to be a deploy step, not a
   project, so that every env converges on its own.
4. As an admin, I want the users page to keep showing emails, so
   that admin work stays possible.
5. As a dev, I want one normalization rule, so that every path
   hashes the same value.
6. As a dev, I want uniqueness enforced in the database, so that
   races cannot create duplicate accounts.

## Implementation Decisions

- One platform KMS key wraps everything. Per-tenant keys are dropped
  (.agents/memory/decisions/platform-key-only.md). Spec A provisions
  the key before this spec lands.
- Email normalizes to lowercase and trimmed at every input
  boundary, in one helper. Pydantic EmailStr validates but does not
  lowercase, so the helper is the single normalization home.
  Identity becomes case-insensitive. This is an accepted behavior
  change: addresses differing by case collapse into one account.
- users.email becomes EncryptedString. Its unique flag and index
  drop; the column keeps carrying the envelope.
- users.email_hash is unique and indexed. It holds base64 of
  HMAC-SHA256 over the normalized email. It is keyed so the hash
  column resists offline guessing.
- The HMAC key is platform-wide and NOT stored like a DEK. It gets a
  dedicated row in its own small table, wrapped under the platform
  key. It never touches tenant_deks (tenant-keyed, auto-generating,
  and deleted on account removal) and never lives in env. The
  composition root unwraps it once through the Cipher port and holds
  it in process.
- All exact-match call sites switch to hash lookup:
  _ensure_email_free is the single duplicate check behind register,
  register_passwordless, setup bootstrap, and admin create;
  authenticate and get_by_email are the two lookup homes.
- Reads that need plaintext re-scope per row: resolve the user's
  tenant from user_tenants, enter that scope (overriding the
  ambient one), decrypt. Four call sites need it: the password
  reset send, the activation link send (unauthenticated requests,
  no scope), and the admin list and get (requests scoped to the
  ADMIN's tenant by the middleware, where other users' envelopes
  fail AES-GCM authentication). Same-tenant sends, like the
  password change notice, keep working under the ambient scope.
- Mail send sites stay correct: the address is decrypted at send
  time under the row owner's scope.
- email_suppressions and email_send_counters stay plaintext-keyed.
  Provider webhooks deliver plaintext addresses, so those tables
  must match them.
- Migrations ride the existing path (apps/api alembic via db_cli;
  Railway boots with API_AUTO_MIGRATE=1 and runs db-upgrade before
  uvicorn). The schema migration adds email_hash nullable with its
  unique index (Postgres unique allows many NULLs). The data
  conversion runs right after the upgrade, before the app serves:
  entrypoint and lifespan run a new db-encrypt-emails command when
  auto-migrate is on; local and devcontainer run
  `uv run db-upgrade && uv run db-encrypt-emails`.
- The conversion is idempotent: it converts only rows with a NULL
  hash. It reads the legacy plaintext with raw SQL, because through
  the ORM the column already decrypts and would raise. It
  normalizes, hashes, and encrypts in place. A case-collision
  between two rows aborts the run loud and lists the rows; the
  operator merges or removes, then reruns. A later migration
  enforces NOT NULL once backfill is guaranteed by the boot path.
- ORM and migration stay catalog-equivalent, per the field-encryption
  lesson (information_schema checks on scratch databases).
- The boot tripwire stays a requirement: with an EncryptedString
  column in the model and no crypto env, lifespan still raises and
  boot aborts. A boot-level test pins this for the new column.

## Testing Decisions

- Live tests against Infisical cover the full path: register, login
  with any case, reset, admin list, and roundtrip decrypt.
- Unit tests use fakes for the crypto module. They pin:
  normalization, hash determinism, unique violation on a duplicate
  hash, re-scope decrypt under the row owner's tenant, and loud
  failure when crypto is unconfigured.
- The conversion gets its own tests: NULL-hash rows convert, run
  twice changes nothing, collision aborts and lists, plaintext read
  bypasses the ORM column.
- Existing suite call sites that filter `User.email ==` in SQL
  (registration, roles, auth, password flows, users, commit boundary
  tests) switch to the hash column or shared factories. Touched test
  files run through falsegreen and the smell review.
- Migration tests check the catalog, not create_all, on a scratch
  database.

## Out of Scope

- Encrypting email_suppressions and email_send_counters.
- Substring search over emails.
- Per-tenant keys.
- Changes to the login handshake shape.
- Encrypting other columns; a later spec reuses this seam.

## Further Notes

- Depends on Spec A (docs/specs/planned/platform-key-provisioning/):
  the platform key must exist and be configured before the first
  encrypted write, or boot fails by design (the lifespan tripwire
  checks ORM metadata, so new-model code without env fails even on
  an empty table).
- The visual lives beside this file in spec.html.
