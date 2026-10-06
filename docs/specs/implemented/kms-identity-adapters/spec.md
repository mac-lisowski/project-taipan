# Spec: Split InfisicalKms along the two-identity seam

Status: implemented (#8)

Seam: unchanged. The existing `Cipher` and `Provisioning` ports are
the test surface. What changes is which adapter a token can reach.

## Problem Statement

`docs/infisical.md` documents two machine identities with different
powers: an admin token that provisions projects, keys, and
rotation, and a `cryptographic-operator` token that can only
encrypt and decrypt. Today that rule exists only in prose. One
class, `InfisicalKms`, implements both ports, so an object built
with a runtime token still offers `rotate` and `create_project`.
The violation is discovered at runtime as an HTTP 4xx, not at the
interface. The type structure does not encode the identity model.

## Solution

Two adapters over one shared private transport. `InfisicalCipher`
implements `Cipher` (encrypt, decrypt) and is what runtime code is
handed. `InfisicalProvisioner` implements `Provisioning`
(project, key, delete, rotate) plus `Cipher`, since the admin
identity can do both. A caller holding a runtime token literally
cannot name a provisioning method. The two-identity rule moves
from documentation into the types.

## User Stories

1. As a developer, I want a cipher adapter exposing only
   `encrypt`/`decrypt`, so that runtime code cannot name `rotate`.
2. As a developer, I want a provisioner adapter for admin
   operations, so that tests and ops request admin powers
   explicitly.
3. As an operator, I want the type structure to mirror the
   documented two-identity model, so that the rule cannot drift
   from `docs/infisical.md`.
4. As a developer, I want both adapters sharing one HTTP
   transport, so that request and error plumbing is not
   duplicated.
5. As a test runner, I want the existing four KMS tests unchanged
   in behavior, so that the split is a pure refactor.
6. As a developer, I want a test asserting the cipher adapter has
   no provisioning methods, so that the separation is enforced.
7. As a developer, I want `KmsError` raised identically from both
   adapters, so that error handling stays uniform.
8. As a maintainer, I want the transport private to the package,
   so that the public interface stays just the two ports.
9. As a developer, I want constructing the wrong adapter for a
   token to be a caller mistake visible in code review, not a
   runtime surprise.
10. As a developer, I want `InfisicalKms` replaced cleanly in the
    test fixture, so that no caller of the old class remains.

## Implementation Decisions

- Two adapter classes in the `kms` package. The cipher adapter
  implements `Cipher` only. The provisioner adapter implements
  `Cipher` + `Provisioning` (the admin identity can encrypt too).
- A private transport (shared request helper or injected
  `httpx2.Client`) carries base URL, auth header, timeout, and
  `KmsError` mapping. It is not exported.
- `InfisicalKms` is removed; `__init__` exports the two adapters,
  `KmsError`, and the ports. The test fixture switches to the
  provisioner; crypto calls in tests use whichever adapter is
  under test.
- No HTTP contract changes: same endpoints, same envelopes, same
  error behavior already verified live on v0.165.16.
- Naming keeps the `Infisical` prefix so the backend is obvious
  at the call site.

## Testing Decisions

- Good tests exercise the adapters through the ports against the
  live instance, unchanged from prior art. The seam does not move.
- Existing tests: roundtrip, garbage-ciphertext, rotation, and
  cross-key tests are ported to the new adapters with identical
  assertions. Provisioning calls in the fixture go through the
  provisioner adapter.
- One new structural test: the cipher adapter exposes `encrypt`
  and `decrypt` and does not expose `rotate`, `create_project`,
  `create_key`, or `delete_project`.
- Same gates: `uv run pytest`, `uvx falsegreen`,
  `test-smell-review`, 300 LOC cap.

## Out of Scope

- Async client, the official `infisicalsdk`, other KMS backends.
- Rotation scheduling, rewrap sweeps, runtime wiring into FastAPI.
- Changing the two-identity model itself (it is decided; this
  spec encodes it).
- New KMS endpoints or capabilities.

## Further Notes

- Candidate 3 from the architecture review. Honest counterweight
  recorded there: today's only consumer is the test fixture, which
  legitimately wants both powers. The split pays off when runtime
  code lands; doing it now keeps that future diff small.
- `docs/specs/kms-identity-adapters/spec.html` visualizes the
  adapter split.
