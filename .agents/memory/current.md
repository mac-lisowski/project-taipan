# Current state

- PR #39 open to dev (branch feat/registration-settings-gate,
  worktree /home/mac/projects/moje/project-taipan-registration):
  registration implemented (f44b27a) + docs commit (spec moved to
  implemented with Status implemented (PR #39); three new planned
  specs from the 2026-10-08 architecture review: magic-link-mailer,
  typed-system-settings, bff-result-module).
- On PR merge: squash lands spec move; planned specs stay queued.
- Deferred: resend race (bounded by single use), users.NotFound 500 on
  deleted user between mint and activate, vitest .next exclude,
  arch candidates 3-5 now spec'd (do them as their own passes).
- Open ops: API_APP_BASE_URL in prod API env; test DB container on
  15432 removable after merge; project-taipan-db-1 zombie, user call.
