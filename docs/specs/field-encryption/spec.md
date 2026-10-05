# Spec: Field encryption capability

Status: implemented (#9)

Seam: `packages/crypto`, one deep module: tenant-aware
`encrypt(tenant_id, plaintext)` and `decrypt(tenant_id, envelope)`
over injected edges (Cipher port, DEK store, DEK cache). Plus one
thin ORM adapter beside the models. Capability only; no model field
changes.

## Problem Statement

ADR-0001 decided how encrypted fields will work, but nothing
implements it. The next feature that stores a secret (an API token,
a personal datum) would improvise crypto per feature: hand-rolled
envelopes, no key topology, no cache. The product also requires that
per-tenant keys work in the future, with generic tenants (a tenant is
a user or an organization; organizations are optional) and without
retrofitting the seam when they land.

## Solution

A domain-named `crypto` package owns everything about field
encryption: the versioned envelope format, per-tenant data-encryption
keys (DEKs) wrapped by Infisical KMS keys, the DEK cache, and
tenant-to-key resolution with a default key from config. Decryption
is tenant-bound: an envelope only decrypts inside its own tenant's
scope. A thin `EncryptedString` column type in the api lets any
future model field opt in with one line. No existing field changes;
the first real encrypted field lands in a later feature.

## User Stories

1. As a feature author, I want `encrypt(tenant_id, plaintext)` that
   returns a versioned envelope, so that storing a secret is one call.
2. As a feature author, I want `decrypt(tenant_id, envelope)` that
   returns the plaintext only inside the tenant's own scope, so that
   an envelope copied into another tenant's row cannot be read.
3. As a developer, I want the key id inside the envelope, so that
   rotation and per-tenant keys need no data migration.
4. As an operator, I want data encrypted locally by a per-tenant DEK,
   so that steady-state reads and writes never wait on an Infisical
   round trip.
5. As an operator, I want DEKs wrapped by Infisical KMS keys and the
   wrapped form stored in Postgres next to the data, so that
   durability and backups match, and a Postgres restore is paired
   with an Infisical restore.
6. As an operator, I want unwrapped DEKs cached in Redis with a TTL,
   so that Infisical is touched only on cache miss and eviction is
   harmless (one unwrap per key).
7. As an operator, I want Redis downtime to degrade instead of fail:
   cache errors are logged and the module unwraps per use, so that
   reads keep working.
8. As an operator, I want Infisical downtime to fail closed: cold
   writes and cache-miss reads fail the operation loudly, warm reads
   keep working, and there is no plaintext fallback.
9. As a maintainer, I want the resolver interface tenant-aware from
   day one, so that per-tenant keys later change only the resolver.
10. As an operator, I want a default KMS key from config, so that the
    capability works before per-tenant keys exist.
11. As a future tenancy feature, I want the resolver substitutable,
    so that a tenants table can supply per-tenant key ids without
    touching the crypto module.
12. As a developer, I want an `EncryptedString` column type beside
    the models, so that opting a future column in is one line.
13. As a maintainer, I want the package domain-named and free of
    SQLAlchemy, FastAPI, and app imports, so that any app can reuse
    it.
14. As a reviewer, I want one error type with stable category codes
    from the crypto module, and no key ids, nonces, ciphertext, or
    plaintext in errors or logs, so that error handling is uniform
    and nothing sensitive leaks.
15. As an operator, I want rotation to be a KMS key version change
    with no data migration, old wrapped DEKs staying on their old key
    versions, so that KMS keys that ever wrapped a DEK are never
    deleted or disabled.
16. As a developer, I want a strict envelope grammar, so that any
    malformed envelope raises the module error instead of leaking
    parse failures.
17. As an operator, I want DEK creation to be race-safe across
    processes, so that concurrent cold starts cannot make data
    undecryptable.
18. As a reviewer, I want ADR-0001 implemented as written, so that
    the record matches reality.

## Implementation Decisions

- New package `crypto` (domain-named, under `packages/`). It depends
  only on the `kms` package's `Cipher` port, a crypto library for
  AES-256-GCM, and its own injected edges. No SQLAlchemy, no
  FastAPI, no app imports. The tenant context variable lives in this
  package (stdlib `contextvars`); callers set it explicitly: tests
  now, request middleware later.
- Injected edges (ports defined by the package):
  - `Cipher` (from `kms`): wraps and unwraps DEKs.
  - Dek store: durable per-tenant wrapped DEKs,
    `get(tenant_id)` / `put(tenant_id, wrapped)`. The api implements
    it over its existing ORM; storage is one small table (tenant id
    unique, key id, wrapped DEK). Put is get-or-create: insert with
    conflict handling, then read back the stored row and adopt it,
    so a racing process never encrypts under a DEK that lost the
    race.
  - Dek cache: optional `get` / `put` for unwrapped DEKs with a TTL.
    The api implements it over Redis behind a short-TTL process-local
    L1, so a warm field operation costs no Redis round trip and L1
    staleness is bounded by its TTL. Absent cache means every use
    unwraps, which is correct but slow. Cache errors degrade: log
    and continue without the cache.
- Tenant resolution: the module's interface is tenant-first. The
  default implementation resolves every tenant to the default KMS
  key id from config (`API_INFISICAL_KMS_KEY_ID`); consequently all
  tenants share one DEK until per-tenant keys land, and the blast
  radius of that shared DEK is every encrypted row. A future tenancy
  feature substitutes a resolver that consults the tenant row.
- Tenant binding: the DEK encrypts with AES-256-GCM using the tenant
  id and key id as associated data. Decrypt takes the tenant id and
  refuses to decrypt under a different tenant: envelope swapping
  between tenants fails the authentication tag.
- Envelope format:
  `v1:<key_id>:<b64url nonce>:<b64url ciphertext>`; exactly four
  fields, literal version `v1`, key id in UUID charset, 12-byte
  nonce, unpadded urlsafe base64. Anything else raises the module
  error.
- Unwrap is single-flight per tenant: the store row and cache are
  tenant-keyed, so the tenant is the unit of duplication. In-process
  and best-effort; concurrent cold unwraps in one process trigger
  one Infisical call. Concurrent cold creates are adoption-safe
  instead: the loser of the store race adopts the winner's DEK, per
  the ADR amendment. A failed unwrap is never negatively cached;
  waiters retry or re-contend. Cross-process stampede prevention is
  out of scope. Tail note: once per TTL window per tenant per
  process, a decrypt waits on Postgres plus Infisical (15 s
  transport timeout), and an Infisical outage repeats that wait
  because failures are never cached. A circuit breaker is future
  work, spec'd in `docs/specs/field-encryption-hardening/`.
- Database schema: the wrapped-DEK table ships as an Alembic
  revision plus an ORM model beside the api models. The
  `cryptography` library belongs to the crypto package, which owns
  all AES-GCM use; the `redis` client package enters the api
  dependency set.
- Errors: the package raises one `CryptoError` with a stable category
  code (unknown envelope version or grammar, decrypt failure, wrap
  failure, missing tenant scope, unknown DEK). KmsError arrives from
  the Cipher port and is wrapped in `CryptoError` at the same seam.

## Testing Decisions

- Good tests assert external behavior only: plaintext in, envelope
  out; envelope in, plaintext out; cache counts; error categories.
  No tests on private helpers, and no key material in asserted
  messages.
- Unit layer: stub `Cipher`, dek store, and cache. Cases: envelope
  grammar (each malformed variant), round-trip, tampered ciphertext
  fails, unknown version fails, tenant-bound decrypt (another
  tenant's envelope fails), resolver fallback to the default key,
  single-flight unwrap (one `Cipher` call under concurrency), failed
  unwrap is not cached, cache hit after first use, get-or-create put
  race (the loser adopts the stored DEK), decrypt with a missing DEK
  row raises the module error.
- Edge-adapter layer: the Postgres DekStore round-trips against the
  test database and enforces uniqueness under a simulated race; the
  Redis DekCache honors TTL semantics against the test Redis or a
  fake with the same contract.
- ORM layer: in-memory database, stubbed crypto module, explicit
  context: column round-trips; encrypt outside scope raises; the
  one-tenant-per-flush rule is documented at the column.
- Live layer: real Infisical through the real adapters, reusing the
  KMS test conventions (skip when the instance or token is missing;
  transport-error tests never skip). Cases: full round-trip through
  the real adapters, and rotate-then-unwrap: after `rotate`, a stored
  wrapped DEK still unwraps (pins the versioned-key assumption).
- After editing tests: `uvx falsegreen`, then `test-smell-review`.

## Out of Scope

- Encrypting any existing model field (email, passwords stay as
  they are); the first real field lands with a later feature.
- The tenants table, tenant type discrimination, and `tenant_id`
  relations on existing tables; the tenancy feature owns them.
- Request middleware or FastAPI wiring for the tenant context.
- Cross-process single-flight locks, rewrap jobs, blind indexes,
  searchable encryption, DEK leak response tooling.
- Deleting the repository layer; that rides with the users-slice.

## Further Notes

- Implements ADR-0001 (`docs/adr/ADR-0001-seam-for-encrypted-model-fields.md`):
  decrypt is tenant-bound, DEKs are per tenant, and the mixed-scope
  flush is a documented rule, not a detectable error.
- Operator docs touch list for tickets: `docs/infisical.md` (paired
  restore dependency; never delete a KMS key that wrapped DEKs) and
  `.env.example` (two new optional cache TTL vars, no new required
  vars).
- Visual map: `docs/specs/field-encryption/spec.html`.
