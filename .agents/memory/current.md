# Current state

- BFF result module IMPLEMENTED on feat/bff-result-module (worktree
  project-taipan-bff-result, off dev 919f779). Four tickets in
  .scratch/bff-result-module/issues/ with reports beside them.
  OPEN as PR #43 to dev. 168 web vitest green. ApiResult in
  apps/web/src/lib/api-result.ts is the one shape; api-detail.ts
  deleted; register.ts no longer imports from app. session.ts app
  import remains, out of spec scope, known follow-up. Spec moves to
  docs/specs/implemented/ at merge.
- Typed system settings MERGED to dev (PR #41 squash 74be3b3).
  Settings public surface is the typed pair only; raw get, set, and
  key constant private; export-pin test added.
- Magic-link mailer MERGED to dev (PR #42 squash 644294f). One link
  mail module owns app mail.
- Users table MERGED to dev (PR #40 squash 919f779). Owner page
  /users over existing GET /api/users; API untouched.
- Web UI on shadcn registries: official base-nova primitives plus
  @reui second registry (decisions/ui-registry.md). Registration
  toggle MERGED (c38cffe) with revert-on-failed-save fix.
- Deferred: resend race (bounded by single use), users.NotFound 500
  between mint and activate, render/browser tests (no harness), users
  list stays instance-wide until invite spec scopes it.
- Open ops: API_APP_BASE_URL in prod API env; test DB container on
  15432 removable; project-taipan-db-1 zombie, user call;
  project-taipan-registration worktree removal, user call.
