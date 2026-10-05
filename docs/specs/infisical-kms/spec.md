# Spec: Infisical KMS client + integration tests

Status: implemented

Seam: `KmsClient` against the real Infisical HTTP API. No mocks.
One seam, same boundary production code uses.

## Problem Statement

The project runs a self-hosted Infisical instance for secrets and key
rotation, but nothing in the codebase can call it. Env vars exist
(`API_INFISICAL_URL`, `API_INFISICAL_TOKEN`) with nothing reading them,
and there is no proof the api can encrypt, decrypt, or rotate against
the live instance. Without a client and tests, the KMS integration is
unverified infrastructure.

## Solution

A small `kms` workspace package wrapping the Infisical KMS REST API,
consumed by the api app, with integration tests that provision a
throwaway KMS project and key, then prove encrypt/decrypt and rotation
semantics against the real service. The operator setup process
(bootstrap, project, key, machine identity, env vars) is documented so
the path from empty instance to working encryption is repeatable.

## User Stories

1. As a developer, I want a typed `KmsClient` in a shared package, so
   that api (and future services) encrypt and decrypt data without
   duplicating HTTP plumbing.
2. As a developer, I want `encrypt(key_id, plaintext: bytes)` returning
   ciphertext, so that call sites handle bytes not base64 plumbing.
3. As a developer, I want `decrypt(key_id, ciphertext)` returning
   plaintext bytes, so that stored ciphertext round-trips cleanly.
4. As a developer, I want `rotate(key_id)` returning the new version,
   so that rotation is a one-call ops action.
5. As a developer, I want API failures raised as a typed `KmsError`, so
   that error handling does not inspect HTTP internals.
6. As a test runner, I want tests to self-provision a KMS project and
   key through the API, so that no manual setup step gates the suite.
7. As a test runner, I want provisioned resources deleted after the
   run, so that the instance does not accumulate junk projects.
8. As a test runner, I want tests to skip when the instance is
   unreachable or no token is set, so that environments without
   Infisical do not fail.
9. As a developer, I want a test proving ciphertext encrypted before
   rotation still decrypts after, so that the core rotation guarantee
   is under test.
10. As a developer, I want a test proving ciphertext under one key
    cannot decrypt under another, so that key isolation is verified.
11. As an operator, I want docs covering bootstrap, KMS project,
    AES-256-GCM key (export off), machine identity (Token Auth,
    `cryptographic-operator`), and env vars, so that setting up a fresh
    instance is a checklist.
12. As an operator, I want `API_INFISICAL_KMS_KEY_ID` documented in
    `.env.example`, so that wiring a pre-made key is a config change.
13. As an operator, I want Railway gotchas documented (`SITE_URL` needs
    `https://`, same-region Postgres, `ENCRYPTION_KEY` backup), so that
    known failures are not rediscovered.

## Implementation Decisions

- New package `packages/kms` (user decision over api-internal).
  Auto-included by the `packages/*` workspace member glob. `uv_build`
  backend, `module-name = "kms"`, dependency `httpx2>=2.13.1` (the
  repo's HTTP client; plain `httpx` is not installed).
- Adapter pattern: a port protocol exposes `encrypt`, `decrypt`,
  `rotate` plus provisioning ops; `InfisicalKms` is the adapter over
  httpx2. Call sites depend on the port, so a different backend (the
  official SDK, a cloud KMS) is a new adapter, not a rewrite.
  `KmsError` on non-2xx responses. Sync client.
- Official `infisicalsdk` was evaluated and rejected for now: it lacks
  `rotate` and workspace provisioning, and pulls boto3/requests into a
  repo standardized on httpx2. Revisit if the SDK catches up; the port
  makes that a drop-in change.
- `api` depends on `kms` via the workspace source mapping, same
  pattern as `core`. Only tests consume it for now.
- Verified API contract (probed live on v0.165.16):
  - `POST /api/v2/workspace` `{projectName, type:"kms"}` returns project
  - `POST /api/v1/kms/keys` `{projectId, name,
    encryptionAlgorithm:"aes-256-gcm", keyUsage:"encrypt-decrypt"}`
    returns key
  - `POST /api/v1/kms/keys/{id}/encrypt` `{plaintext: base64}` returns
    `{ciphertext}`
  - `POST /api/v1/kms/keys/{id}/decrypt` `{ciphertext}` returns
    `{plaintext: base64}`
  - `POST /api/v1/kms/keys/{id}/rotate` returns key with `version++`
  - `DELETE /api/v1/workspace/{projectId}` deletes the project and its
    keys (fixture teardown)
- Rotation semantics verified: ciphertext under v1 decrypts after
  rotate to v2.
- No DB schema changes. No Alembic migration.
- `docs/infisical.md` holds the operator checklist; README links it.
  `apps/api/.env.example` gains `API_INFISICAL_KMS_KEY_ID`.
- Token model: tests need an admin-capable token (bootstrap machine
  identity) for self-provisioning. The runtime api token uses the
  `cryptographic-operator` role and only encrypts and decrypts.

## Testing Decisions

- Good tests assert on the client boundary against the real service:
  encrypt/decrypt round-trip, rotation preserving decryption, cross-key
  isolation. Not HTTP internals.
- Tested modules: the `kms` client and admin provisioning, driven from
  `apps/api/tests/test_infisical_kms.py` so the api to Infisical
  integration is what is proven.
- Prior art: `apps/api/tests/test_infisical.py`, skip-when-unreachable
  via `pytestmark`, env-var configuration.
- Session-scoped fixture: reachable instance plus `API_INFISICAL_TOKEN`
  set, creates project and key, yields the key id, deletes the project
  on teardown.
- Gate: `uvx falsegreen` structural pass plus test-smell review before
  commit.

## Out of Scope

- Field-level encryption of Postgres rows (envelope encryption in
  models is the future consumer).
- Universal Auth for machine identities; Token Auth only.
- Blind indexes and searchable encryption.
- Scheduled key rotation and ciphertext rewrap sweeps.
- FastAPI endpoints exposing KMS operations.
- CI execution; tests skip where no Infisical instance exists.

## Further Notes

- Encryption keys are not exportable (user decision). The backup story
  is a Postgres dump plus the `ENCRYPTION_KEY` env var.
- `cryptographic-operator` is least privilege for the api identity.
  Rotation is an ops action, not an api credential right.
