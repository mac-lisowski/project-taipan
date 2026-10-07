# Current state

- Branch feat/password-reset (rebased on origin/dev cbd5b68: litellm #36 +
  ci commits merged in). Password-reset spec IMPLEMENTED; this commit carries
  the whole feature. PR to dev in flight; spec moves to docs/specs/implemented/
  in the follow-up docs commit with the PR number.
- API: password_reset module (request/reset acts; strength check BEFORE
  tokens.verify because verify burns atomically; revoke_all BEFORE
  auth_flow.issue; best-effort neutral mail), routers /auth/forgot (always 204)
  + /auth/reset (400 "invalid or expired reset link" / 422 "weak password";
  exact strings are the client's only signal), config API_RESET_TOKEN_TTL_SECONDS
  (3600) + API_APP_BASE_URL (http://localhost:3000, empty falls back),
  users.get_by_email, set_token_store + autouse memory_token_store fixture
  (reset is the first HTTP caller of tokens). Schemas ForgotIn/ResetIn.
- Web: /reset page (Next 16 awaited searchParams, no useSearchParams),
  ResetForm (verbatim upstream errors, token fixed for retry),
  lib/reset-password.ts (RESET_LANDING = /dashboard), forgot-form mock
  comment replaced with why-comment.
- Gates at stamp: root pytest 396 passed 9 skipped (live KMS), web vitest 168,
  web build clean, ruff clean, falsegreen + falsegreen-js clean, file-size +
  bff pass. code-review two-axis CLEAN after 4 fixes (empty app_base_url
  fallback, comment trim, HTTP used-token 400 pin, store docstring). Stamp on
  this tree: 225958677d1c0715 lineage. test-smell-review: 1 LOW accepted
  (broad TokenError assert in inactive-rejection module test).
- test_url_ownership.py repaired in passing: pre-existing assert-after-restore
  bug; failed whenever API_TEST_* env vars were set.
- Deferred review notes (not defects): APP_NAME duplicated from
  password_change/notice.py; register/authenticate keep inline email selects;
  memory_token_store mirrors memory_session_store shape; reset-form hand-rolls
  pending/error (same useAuthSubmit follow-up as password-change); expired-token
  400 pinned at module seam, unknown+used pinned at HTTP.
- Tickets 01+02 done with HTML reports in .scratch/password-reset/issues/
  (gitignored). Disposable test DB container taipan-password-reset-test-db on
  host 15432: REMOVE after merge. project-taipan-db-1 is a zombie (no network,
  host 5432 held by python-playground-db-1, rootless docker): untouched, user
  decision.
