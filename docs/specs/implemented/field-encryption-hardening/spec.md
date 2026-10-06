# Spec: Field-encryption hardening

Status: implemented.

The capability is complete and verified live. This spec lands the
three follow-ups the whole-scope review deferred: fail-fast on KMS
outage, deduplicated api test helpers, and public accessors that end
private-state assertions in wiring tests.

## Problem Statement

Infisical is down or slow. The first caller per tenant waits on the
full 15 s transport timeout, and because failed unwraps are never
cached, every cold caller repeats that wait until Infisical returns.
A tenant-scoped query can stack dozens of these waits. Callers cannot
distinguish "KMS unreachable" from a data problem because both arrive
as decrypt failure. Separately, the review left two hygiene debts:
api test files repeat the same fakes and constants, and wiring tests
assert on two levels of private attributes, so refactors break tests
that test nothing.

## Solution

A circuit breaker wraps the Cipher port. After N consecutive KMS-side
failures it opens and every unwrap or wrap fails fast with one stable
error code; after a cooldown one probe call decides between closing
and staying open. The api composition root wires it around the real
Infisical adapter with env-configurable threshold and cooldown. Api
test helpers move into one shared module, and FieldCrypto and the
two-tier cache expose read-only accessors so tests assert wiring
through public surface.

## User Stories

1. As an api caller, I want cold operations to fail fast while the
   KMS is down, so that requests fail in milliseconds instead of
   hanging for the 15 s transport timeout.
2. As an api caller, I want one stable error category for "key
   service unavailable", so that I can retry or degrade without
   parsing message text.
3. As an operator, I want the breaker threshold and cooldown
   configurable by env, so that I can tune fail-fast behavior per
   environment without a code change.
4. As an operator, I want the breaker shared by the whole process,
   so that one tenant's cold unwrap failing teaches every later
   caller in that window.
5. As a developer, I want the breaker to close again on success, so
   that recovery needs no restart or deploy.
6. As a developer, I want the breaker state machine unit-tested
   through the Cipher port, so that no test needs a live Infisical.
7. As a reviewer, I want each breaker transition covered by a
   discriminating test, so that the state machine cannot regress
   silently.
8. As a developer, I want decrypt-authentication failures to be
   distinguishable from outage failures, so that data problems never
   trip the breaker.
9. As a maintainer, I want api test helpers in one module, so that a
   fake or constant changes in one place.
10. As a developer, I want unique tenants and key ids shared by the
    edge and live test files, so that collisions stay impossible as
    tests grow.
11. As a reviewer, I want wiring tests to assert through public
    accessors, so that internal refactors do not break tests.
12. As a developer, I want read-only accessors on the module and its
    cache, so that introspection needs no underscore pokes.
13. As an operator, I want the breaker behavior documented beside the
    existing tail-latency note, so that the spec stays the single
    source of runtime posture.
14. As a maintainer, I want the crypto package to stay free of
    timing deps beyond injectable clocks, so that tests stay
    deterministic.

## Implementation Decisions

- New `BreakerCipher` in the crypto package: a decorator implementing
  the existing Cipher port over any wrapped Cipher. No I/O, no
  threading beyond a lock around transitions, injectable clock for
  cooldown and tests.
- State machine: closed passes calls through and counts consecutive
  KMS-side failures; at the threshold it opens. Open raises
  immediately with the new stable category `kms_unavailable` without
  touching the wrapped Cipher. After the cooldown it admits one probe
  call; probe success closes and resets, probe failure re-opens and
  restarts the cooldown. Any success while closed resets the count.
- Only `KmsError` from the wrapped Cipher counts as a failure. The
  module's own decrypt authentication failure never reaches the
  breaker, so tampered or cross-tenant data cannot open it.
- `CryptoCategory` gains `kms_unavailable`. Existing codes do not
  change. Messages stay free of key material and endpoint details.
- The api composition root wraps the Infisical adapter in the breaker
  when building the module. Threshold defaults to 3, cooldown to 30
  seconds; optional env vars follow the existing `API_` naming.
  Without config the capability stays off exactly as today.
- A shared apps/api test support module hosts the duplicated helpers:
  unique tenant factory, the shared key-id constant, the base64 stub
  cipher, and the in-memory store fake. The edge and live test files
  import them. Cross-package duplication with the crypto package's
  own fakes is deliberate and stays.
- `FieldCrypto` exposes read-only `cipher`, `store`, and `cache`
  accessors; the two-tier cache exposes `local` and `remote`. Wiring
  tests assert types through these. No test reads private attributes
  anymore.
- Cache-content assertions stop hardcoding the `crypto:dek:` Redis
  key prefix. Tests assert presence through the `remote` accessor;
  if a key-format assertion is truly needed, the adapter exposes
  the prefix constant rather than tests reimplementing it.
- `packages/kms` gets its own `tests/` directory. The adapter and
  transport tests that need no api move out of `apps/api/tests`
  with the same skip conventions; api-scoped integration tests
  stay. The package becomes self-verifying, matching the crypto
  package's convention.
- The spec's tail-latency note is updated: the breaker is no longer
  future work; the note names the new category and defaults.

## Testing Decisions

- Good tests assert external behavior: call outcome and error
  category, never internal state or call order beyond what the
  contract promises.
- Breaker unit tests live in the crypto package: closed-then-opens at
  threshold, open fails fast with zero wrapped-Cipher calls,
  cooldown admits exactly one probe, probe failure re-opens,
  probe success closes, success resets the count. A fake clock makes
  cooldown deterministic; no real sleeps.
- Api wiring tests assert the built module's cipher is the breaker
  wrapping the Infisical adapter, through the new accessors.
- Prior art: the crypto package's stubbed-edge unit suite and the
  api edge tests with fakes and fake clocks.

## Out of Scope

- Negative caching of failures or success-path memoization.
- Circuit breaking on the DekStore or DekCache edges; the breaker
  wraps only the Cipher port.
- Cross-process breaker coordination; the breaker is per process.
- Per-tenant breakers; the breaker guards the shared KMS endpoint.
- AESGCM instance caching (measured 0.6 microseconds per operation,
  not worth the invalidation complexity).
- Changing the never-cache-failed-unwrap rule or single-flight.

## Further Notes

- Origin: whole-scope review of the field-encryption capability.
  The perf review measured the outage tail and deferred the
  breaker; the smell review deferred the helper dedup and the
  accessor refactor.
- `docs/specs/implemented/field-encryption-hardening/spec.html` visualizes the
  breaker state machine and the accessor surface.
