# Current state

- Branch: `dev` at 9382387 (PR #34 squash-merged).
- Password change DONE: api/password_change/ domain module, POST
  /api/account/password (wrong current 401, weak/same-as-old/mismatch
  422, signed-out 401), REVOKE_OTHER_SESSIONS revoke-all + re-mint,
  best-effort notice via PASSWORD_CHANGE template (packages/email,
  per-template required fields), web account form (display-only
  strength bar, submitAuth carries success body, changePassword
  delegates to it).
- Two review rounds clean; workspace 360 passed 9 skipped at merge,
  web vitest 135.
- GOTCHA: apps-before-packages pytest order breaks email log test
  (alembic fileConfig disables loggers). Default testpaths order safe.
- Next candidates: fold form pending/error into useAuthSubmit;
  architecture review 3/5 unpicked candidates (see zcode memory).
