# Current state

- Registration MERGED to dev (PR #39). Spec lives in docs/specs/implemented/registration/.
  Three planned specs queued:
  magic-link-mailer, typed-system-settings, bff-result-module. Do each
  as its own implement-spec pass.
- Worktree /home/mac/projects/moje/project-taipan-registration still
  exists on the merged branch (ticket reports in its .scratch/): user
  decides removal. Remote branch not deleted.
- Deferred: resend race (bounded by single use), users.NotFound 500 on
  deleted user between mint and activate, vitest .next exclude,
  APP_NAME x3 + BFF parser (spec'd in the planned specs).
- Open ops: API_APP_BASE_URL in prod API env; test DB container on
  15432 removable now that both PRs merged;
  project-taipan-db-1 zombie, user call.
