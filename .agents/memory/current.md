# Current state

- Settings page registration control is now a shadcn Switch toggle
  (base-nova). Uncommitted on dev: components.json (@reui registry),
  ui/components/switch.tsx (new), ui/index.ts, settings page switch.
  User reviews diffs before commit; awaits approval.
- reUI registry `@reui` live in apps/web/components.json. Bare
  primitives stay on official shadcn; `@reui/<name>` for composites;
  pro items 401 without license.
- Registration MERGED to dev (PR #39). Spec in
  docs/specs/implemented/registration/. Three planned specs queued:
  magic-link-mailer, typed-system-settings, bff-result-module.
- Deferred: resend race (bounded by single use), users.NotFound 500 on
  deleted user between mint and activate, vitest .next exclude,
  APP_NAME x3 + BFF parser (spec'd in the planned specs).
- Open ops: API_APP_BASE_URL in prod API env; test DB container on
  15432 removable; project-taipan-db-1 zombie, user call;
  project-taipan-registration worktree removal, user call.
- Known web gap: no render/browser tests for the toggle component.
