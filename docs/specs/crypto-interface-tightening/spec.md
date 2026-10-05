# Spec: Tighten the crypto module's interface

Status: not implemented.

Seam: the crypto package's public surface. No new seams; this spec
removes surface that lets callers bypass the module's own rules.

## Problem Statement

The crypto package exports more than its guarantees cover. The raw
`tenant_ctx` ContextVar is re-exported, so a caller can `set()` a
tenant without `tenant_scope`'s reset and leak it into later
flushes. `DekManager` is exported even though constructing it
directly skips `FieldCrypto`'s scope checks. `DekCache.put` carries
a `ttl_seconds` parameter that the only production caller always
passes as `0`, so every adapter implements a convention with zero
callers. `serialize` writes whatever key id it is given, but
`parse` rejects non-UUID key ids. A malformed
`API_INFISICAL_KMS_KEY_ID` produces envelopes the module itself
cannot decrypt. The failure shows at first decrypt instead of at
startup.

## Solution

Cut the surface to what callers use: drop the dead cache parameter,
stop re-exporting the internals, and make the write path enforce
the same grammar the read path enforces. Config errors fail at
construction time, not at first decrypt.

## User Stories

1. As a maintainer, I want `DekCache.put` to carry no per-call TTL,
   so that adapter authors implement only behavior with callers.
2. As a maintainer, I want each cache adapter to own its TTL, so
   that the "non-positive defers" convention disappears.
3. As a developer, I want the raw `tenant_ctx` ContextVar
   unexported, so that the only way to set scope is the reset-safe
   `tenant_scope` helper.
4. As a developer, I want `DekManager` unexported, so that all
   encrypt/decrypt traffic passes through `FieldCrypto`'s scope
   checks.
5. As an operator, I want a malformed key id rejected at startup,
   so that misconfiguration cannot produce undecryptable data.
6. As a maintainer, I want `serialize` and `parse` to enforce the
   same grammar, so that the write path can never emit what the
   read path rejects.
7. As a reviewer, I want the package's `__all__` to equal its
   contract, so that the interface is readable in one screen.
8. As a test writer, I want tests to keep importing internals from
   their defining modules, so that the export cut costs nothing in
   coverage.

## Implementation Decisions

- `DekCache.put(tenant_id, dek)` drops `ttl_seconds`. Adapters own
  their TTLs: the local TTL cache uses its configured value, the
  Redis cache uses its configured value, the two-tier adapter just
  fans out. `DekManager` stops passing a TTL.
- Tests that pinned the per-call TTL convention are rewritten to
  assert each adapter's configured TTL, or deleted if redundant.
- `crypto.__init__` stops exporting `tenant_ctx` and `DekManager`.
  Both stay importable from `crypto.context` / `crypto.deks` for
  the package's own tests. No production caller uses either.
- `serialize` validates the key id with the same rule `parse`
  applies (v1 grammar, UUID shape) and raises `ENVELOPE_GRAMMAR`
  on a bad id, so every writer path is covered symmetrically.
- The api composition root validates `API_INFISICAL_KMS_KEY_ID`
  before building the module, so env misconfig fails at startup.
- `parse`, `NONCE_BYTES`, `DefaultKeyResolver`, the three ports,
  the context helpers (`tenant_scope`, `current_tenant`,
  `require_tenant`), `FieldCrypto`, and the error types remain the
  public surface.
- No behavior change to correct callers; only callers that never
  existed lose access.

## Testing Decisions

- Good tests assert outcomes through the public surface: encrypt /
  decrypt results, error categories, cache hits through behavior.
- New tests: `serialize` with a non-UUID key id raises
  `ENVELOPE_GRAMMAR`; the composition root rejects a malformed key
  id env var.
- Rewritten tests: the two cache tests that exercised per-call TTL
  overrides now assert the adapter's configured TTL is used.
- Existing round-trip and DEK-lifecycle tests must pass unchanged;
  they are the regression net for the export cut.
- Prior art: `packages/crypto/tests/test_crypto.py` and the api
  edge tests, all stubbed-edge.

## Out of Scope

- The `tenant_deks.key_id` provenance column and the `DekStore`
  port signature; revisit when per-tenant keys land.
- Circuit-breaker and accessor work; owned by
  field-encryption-hardening.
- `LocalTtlDekCache` unbounded growth; a separate small fix.
- Changing the envelope grammar itself.

## Further Notes

- Candidate 3 from the architecture review. Pure tightening: the
  module stays the deep module the ADR ordered, with an interface
  that finally matches what callers actually use.
- `docs/specs/crypto-interface-tightening/spec.html` visualizes the
  surface cut.
