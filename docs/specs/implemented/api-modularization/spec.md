# Spec: API modularization

Status: implemented.

Seam: feature folders with router plus service plus schemas. Shared
authorities own cross-flow truth. Routers stay thin. Models stay
shared. No per-module repos.

## Problem Statement

The API app is layered, not modular. Routers, schemas, and models
sit in flat folders. Domain files float at top level. The repo
folder is empty. Three auth flow specs wait to land. Each repeats
the same token, session, and password rules. Without owned homes,
registration, reset, and change will each mint tokens, write
sessions, and check passwords in their own way. The truths fork
within one quarter.

## Solution

Give each feature a folder with its router, service, and schemas.
Give cross-flow truth to shared authorities. One tokens service
with a purpose column serves activation and reset. One sessions
authority owns mint, revoke, and revoke-all. One credentials
module owns hash, policy, and the activation gate. Users owns
identity plus profiles. Registration, reset, and change become
thin policy orchestrators over these authorities. Setup stays a
thin empty-database guard, not a module. Shared tables and tenant
scoping stay shared.

## User Stories

1. As a developer adding registration, I want one tokens service, so that I never write mint, verify, burn twice.
2. As a developer adding reset, I want the same tokens service with a reset purpose, so that expiry and hashing match activation.
3. As a developer adding a flow that logs in, I want one sessions authority, so that revoke rules stay in one place.
4. As a developer changing password policy, I want one credentials module, so that all flows pick up the rule at once.
5. As a developer reading users, I want identity plus profiles in one place, so that cascade rules cannot cycle.
6. As a developer running setup, I want a thin guard over users plus sessions, so that first run stays a special case of normal paths.
7. As a developer adding a mail flow, I want the shared email seam, so that no flow wires its own sender.
8. As a developer adding social login later, I want credential verifiers to plug into session issue, so that routers never change shape.
9. As a reviewer, I want no per-module repos, so that no single-adapter seam ships without leverage.
10. As a reviewer, I want shared tables to stay shared, so that one migration path serves all modules.
11. As a maintainer, I want tenant scoping in shared middleware plus guard, so that no feature module can drop it.
12. As a tester, I want module seams that accept injected stores, so that flow tests need no database.

## Implementation Decisions

- Feature folders own router, service, and schemas. Registration, password reset, and password change are policy orchestrators. They own flow order and effects. They own no token hashing, no session rows, and no password hashes.
- One tokens service owns mint, verify, and burn over a purpose column. Purposes cover activation and reset today, magic links tomorrow. Flows own time to live and post-verify effects only.
- One sessions authority owns mint, revoke, and revoke-all over the existing sessions table pattern. Reset calls revoke-all then mint. Change keeps current. Registration mints. No flow touches session rows direct.
- One credentials module owns the hasher, the strength rule, and the activation gate. Registration, reset, and change share all three. No second policy ships.
- Users owns identity plus profiles. Profiles nests under users because it already depends on users twice. Cascade rules live with the parent.
- Setup is a thin guard, not a module. It checks the empty database case and delegates to users bootstrap plus sessions mint. No bootstrap logic lives in the guard.
- Tables stay shared. No per-module models and no per-module repos ship. The empty repo folder goes away. Tenant scoping stays in shared middleware plus guard.
- Routers stay thin. They map bodies, call services, map typed errors to status codes, and set cookies. They hold no token, session, or password rules.
- Auth routers issue sessions through verifiers. Password is the first verifier. Token links and future social or passkey verifiers plug the same slot. Router shape does not change per verifier.
- Mail composition stays as is. Flows call the shared email seam. No flow owns templates or adapters.

## Testing Decisions

- Good tests cross module seams with injected fakes. They assert results and typed errors. They do not touch HTTP or the database unless the seam is persistence.
- Tokens tests pin mint, verify, burn, single use, hash at rest, and short expiry per purpose. Flows assert purpose scoping: a reset token never activates.
- Sessions tests pin mint, revoke, and revoke-all through the one authority. Flow tests assert which call the flow made, not row contents.
- Credentials tests pin hash verify, policy accept and reject, and the activation gate. All three flows share these cases by reference.
- Move slices are verified by the existing suite. Each moved module lands with the full suite green. No slice lands with a skipped suite.
- After editing tests, run the structural test check first, then the test smell review. A test that cannot fail is removed.

## Out of Scope

- Per-module tables, migrations, or repo splits.
- Social login, passkeys, and passwordless beyond the token purpose column.
- Session format or password storage changes.
- Mail package or template changes.
- Web app changes.

## Further Notes

- This shape comes from two challenger reviews. Both rejected setup as a module and per-module repos. Both demanded the tokens service before any flow lands.
- The companion visual lives beside this file in spec.html. It shows the authorities, the orchestrators, and the test seams.
