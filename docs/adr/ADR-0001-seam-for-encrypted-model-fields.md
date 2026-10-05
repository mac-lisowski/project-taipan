# ADR-0001: Seam for encrypted model fields

Status: accepted (2026-10-05)
Backed by prototype: .scratch/encryption-seam/prototype.py (throwaway;
verified against live Infisical v0.165.16, then deleted after this
record was written)

## Context

Fields that hold secrets must be encrypted at rest: Postgres stores
only ciphertext. The KMS client exists (packages/kms, two adapters,
live-tested). Two candidate seams place the encrypt/decrypt
conversion at different layers. Picking during feature work instead
of now means rework either way.

Tenancy requirement (decided): the system will use a generic
`tenants` table; a tenant can be a user or an organization, and
organizations are optional. Every tenantable row carries a
`tenant_id`. Each tenant may get its own KMS key in the future. The
encryption seam must speak only of `tenant_id`; tenant type is not
its concern.

## Options

- Option A: column-level `TypeDecorator`. Encryption rides the ORM
  column type. Every read and write converts transparently. Callers
  cannot forget it.
- Option B: repository-owned conversion. The repository encrypts on
  write and decrypts on read. Explicit, but every call site must
  remember the conversion, and the repository layer currently fails
  the deletion test (its interface is its implementation).

## Decision

Option A, with one addition: the deep module is a crypto module, not
the repository.

- `EncryptedString(TypeDecorator)` delegates to a crypto module
  through a request-scoped tenant context.
- The crypto module owns: tenant-to-key resolution, data-encryption
  keys (DEK), the ciphertext envelope format, and encrypt/decrypt.
  It speaks only of `tenant_id`. Tenant type is invisible to it.
- Key topology: the resolver returns one default key from config
  today; when tenancy lands, a tenant row may carry its own key id
  and the resolver implementation changes. The seam does not.
- KMS pattern: envelope encryption. Data is encrypted locally with a
  per-tenant DEK (AES-256-GCM). The DEK is wrapped by the tenant's
  Infisical KMS key and the unwrapped DEK is cached (Redis in
  production). KMS is touched only on cache miss.
- Envelope format: `v1:<key_id>:<nonce>:<ciphertext>`. The key id
  travels inside the envelope: decryption is self-describing, KMS
  rotation (versioned keys) needs no migration, per-tenant keys need
  no extra column, and algorithm changes are additive (v2).

## Verified behavior (prototype outcomes)

- A SQLite row stores only the versioned envelope; no plaintext is
  reachable through the ORM or raw SQL.
- Round-trip through the ORM and the live Cipher port returns the
  original bytes.
- Two tenants encrypting the same secret produce envelopes with
  different key ids and different ciphertext.
- DEK cache: exactly one unwrap per tenant, then cache hits.

## Verified constraint: one tenant scope per flush

The prototype first failed honestly: the column type reads the
tenant context at flush time, not at add() time, so rows added under
two tenant scopes but flushed once were all encrypted under the last
scope. Rule: one tenant scope per flush. With per-request scoping
(one request = one tenant) this holds naturally. Background jobs
must set the scope explicitly per unit of work. The mixed-scope
flush is a documented rule, not a runtime-detectable error: the
column reads the context at flush time and cannot see the mixture.

## Why Option B lost

- Locality: Option B scatters conversion responsibility across every
  repository method; a new query path can bypass it. Option A
  concentrates it in one column type; bypassing requires raw SQL
  with hand-rolled crypto, which review can spot.
- Depth: repositories fail the deletion test today. Keeping them
  alive to hold encryption would reward a shallow layer with a deep
  job. The crypto module is the deep module instead.
- Test surface: both options can stub the Cipher port, but Option A
  needs no repository in tests at all.
- Cost: Option B would be deleted anyway if repositories go; Option A
  plus repository deletion removes a layer instead of dressing it up.

## Consequences

- Repositories become deletable; the feature spec that adds the
  first encrypted field also deletes BaseRepository and
  UserRepository and the deletion-test question closes.
- Ciphertext cannot be filtered, ordered, or joined. Equality lookup
  is added per field later as a keyed HMAC blind-index column. No
  LIKE or range search on encrypted data, ever.
- No migration of existing data: only a password hash exists today.
  The envelope version prefix covers future rewraps.
- Redis becomes a crypto dependency: a DEK cache eviction or flush
  is harmless (the DEK unwraps again from KMS).
- The `cryptography` package (AESGCM) enters the api dependencies in
  the feature spec.

## Resolved questions

- Story 6 (repository fate): deleted in the feature spec.
- Story 7 (test surface): unit tests stub the crypto module's
  transport; integration tests round-trip through the live Cipher
  port with the KMS test conventions (skip when down).
- Story 8 (key-id sourcing): inside the envelope; rotation is a KMS
  key version change, not a data migration.

## Amendment (2026-10-05, challenge review of the field-encryption spec)

- Decrypt is tenant-bound: `decrypt(tenant_id, envelope)`; the tenant
  id and key id are AES-GCM associated data, so an envelope copied
  into another tenant's row fails the authentication tag.
- DEKs are per tenant from day one (store keyed by tenant id, not key
  id); with the default resolver all tenants share one DEK today, and
  that blast radius is stated in the spec.
- Wrapped-DEK creation is get-or-create with conflict adoption, so
  racing processes cannot make data undecryptable.
- Restore pairing: an api Postgres restore is only readable against a
  restored Infisical (its database plus its encryption key).
