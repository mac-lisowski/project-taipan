# Current state

- BFF result module IMPLEMENTED on feat/bff-result-module (worktree
  project-taipan-bff-result, off dev 919f779). Four tickets in
  .scratch/bff-result-module/issues/ with reports beside them.
  OPEN as PR to dev. 168 vitest green.
  ApiResult in apps/web/src/lib/api-result.ts is the one shape;
  api-detail.ts deleted; register.ts no longer imports from app.
  session.ts app import remains, out of spec scope, known follow-up.
  Spec moves to docs/specs/implemented/ at merge.
- Users table OPEN as PR #40 (feat/users-table, head 9ae5504, squash
  to dev pending). Spec in docs/specs/implemented/users-table/. Owner
  page /users over existing GET /api/users; API untouched.
- Web UI on shadcn registries: official base-nova primitives plus
  @reui second registry (decisions/ui-registry.md).
- Registration toggle MERGED to dev (c38cffe) with revert-on-failed-
  save fix (endpoint result is the only source, including errors).
- Two planned specs queued: magic-link-mailer, typed-system-settings.
- Deferred: resend race (bounded by single use), users.NotFound 500
  between mint and activate, render/browser tests (no harness), users
  list stays instance-wide until invite spec scopes it.
- Open ops: API_APP_BASE_URL in prod API env; test DB container on
  15432 removable; project-taipan-db-1 zombie, user call;
  project-taipan-registration worktree removal, user call.
