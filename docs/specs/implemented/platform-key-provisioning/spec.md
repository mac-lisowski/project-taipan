# Spec: Platform KMS key provisioning

Status: implemented (PR #46).

Seam: the Provisioning port in packages/kms gains find operations.
One script in scripts/ owns idempotent provisioning. App code stays
untouched. The admin token never enters the app runtime.

## Problem Statement

The platform field-encryption key is made by hand today.
docs/infisical.md walks the UI flow and README links it. Documented
is not repeatable: the step is manual, easy to skip, and produces no
record. The crypto capability is off when the env is missing. Email
encryption (docs/specs/planned/email-at-rest/spec.md) adds the first
encrypted column, and then boot fails hard without the key. Setup
needs one command that is safe to run twice.

## Solution

Extend InfisicalProvisioner with find operations for projects and
keys. Add one Python script, scripts/provision_kms.py. It finds or
creates the pinned KMS project and key, prints the key id, and
verifies on request that the runtime token can use the key. The
script replaces the manual section in docs/infisical.md and gains a
README step. The app never sees the admin token.

## User Stories

1. As an operator, I want one command that creates or finds the
   project and key, so that setup is repeatable.
2. As an operator, I want the script to print the key id, so that I
   can set `API_INFISICAL_KMS_KEY_ID`.
3. As an operator, I want a verify flag that proves the runtime
   token can decrypt, so that a missing grant fails at setup, not at
   boot.
4. As an operator, I want re-runs to change nothing, so that the
   script is safe to run from docs and CI notes.
5. As a kms dev, I want find operations on the Provisioning port,
   so that create-or-get needs no UI step.
6. As a newcomer, I want a README step, so that first setup needs no
   tribal knowledge.

## Implementation Decisions

- One platform key wraps every tenant DEK. Per-tenant KMS keys are
  dropped (see .agents/memory/decisions/platform-key-only.md).
  KeyResolver, tenant_deks.key_id, and the envelope key id stay as
  the seam in case that ever reverses.
- Names are pinned: project `taipan-field-encryption`, key
  `platform-field-encryption`.
- Find before create. Provisioning gains find_project(name) and
  find_key(project_id, name), both returning the id or None.
- Endpoints, verified live on self-hosted v0.165.16: project list is
  `GET /api/v1/projects?type=kms` (wrapped `{"projects": [...]}`),
  not a workspaces route. That list is membership-scoped: the token
  sees projects it created, which covers the admin-token flow. Key
  lookup is `GET /api/v1/kms/keys/key-name/{name}?projectId=`
  (wrapped `{"key": {...}}`, 404 when absent). Key names are unique
  per project. Project names are not: several exact-name matches is
  a loud error asking for cleanup, never a silent pick.
- Key creation hardens the defaults: body uses `algorithm` (not the
  deprecated `encryptionAlgorithm` alias), `keyUsage`
  encrypt-decrypt, `isExportable` false (matches the no-export
  stance of the crypto interface work), `hasDeleteProtection` true.
- The admin token comes from env var `INFISICAL_ADMIN_TOKEN`, read
  only by the script. The URL var is `API_INFISICAL_URL`, shared
  with app config. The runtime token stays `API_INFISICAL_TOKEN` and
  keeps encrypt-decrypt only. No runtime code reads the admin token.
- The script runs with `uv run python scripts/provision_kms.py` from
  the repo root and imports the kms workspace package. Root
  pyproject declares kms in its dev dependency group for this (today
  it arrives only transitively via api).
- Verify is opt-in via `--verify`. It runs one encrypt-decrypt
  roundtrip with the token in `API_INFISICAL_TOKEN` against the key
  id. In dev that var may hold the admin token, which makes verify
  weak there; the meaningful target is the dedicated `taipan-api`
  machine identity token used by deployed envs.
- Identity-project grants stay manual. On verify failure the script
  prints the step: add the identity to the project with the built-in
  `cryptographic-operator` role (project-scoped, covers all keys in
  it; the membership default is `no-access`). Automating membership
  is out of scope.
- The key id goes to stdout as one line. Human text goes to stderr.
  Nothing is written to files.

## Testing Decisions

- Find operations get live tests against self-hosted Infisical, per
  the packages/kms convention: live_only skip guard, conftest
  self-provisions a throwaway project and key and deletes it after.
- The create-or-get choice is a pure function over finders. Unit
  tests drive it with fakes: project found, project missing, key
  found, key missing, several same-name projects errors loud.
- The verify path is a thin call over the Cipher port. One unit test
  with a fake Cipher pins the failure message shape.
- No runtime code moves. No app tests change.

## Out of Scope

- Per-tenant KMS keys (dropped).
- Rotation automation; provisioner.rotate stays an ops action.
- Identity-project membership automation.
- CI provisioning steps; the script is operator-run for now.
- Spec B schema and email work
  (docs/specs/planned/email-at-rest/spec.md).

## Further Notes

- The visual lives beside this file in spec.html.
- Runtime src never calls the provisioner; only tests do today
  (test_field_crypto_live self-provisions). This spec keeps that
  split.
- Spec B depends on this spec: its boot and migration paths need the
  key to exist before the first encrypted write.
