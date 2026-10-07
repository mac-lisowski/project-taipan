# Current state

- dev at 842e020: registration spec carries the system settings gate.
  Global KV settings table. registration_enabled defaults to false.
  Switch off: API sign up endpoint 404, web register route 404, and no
  sign up links render. Flip is owner-only. Why owner-only lives in
  decisions/system-settings-owner-guarded.md. Next: cut tickets, then
  implement the spec.
- Password-reset is merged (PR #37, squash 0806a5b). Open follow-ups:
  set API_APP_BASE_URL in prod API env, equal to web PUBLIC_ORIGIN, or
  mailed links fall back to localhost. Remove the disposable test DB
  container taipan-password-reset-test-db on host 15432; the merge is
  done. project-taipan-db-1 stays a zombie (host 5432 held by
  python-playground-db-1): untouched, user decision.
