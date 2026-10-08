# Current state

- Dev pushed through 92f41f3: 34a7d97 fixes all 21 falsegreen
  findings (email suite split under the 300-LOC gate: conftest.py +
  test_send_budget.py), 1e57f54 moves bff-result-module,
  magic-link-mailer, litellm-gateway-docker into
  docs/specs/implemented/ (PRs #43, #42, #36), 92f41f3 moves shared
  test helpers into api_testsupport/email_testsupport so the suite
  collects under any pytest arg order.
- docs/specs/planned/ now holds only nats-jetstream (PR #38 open).
- Python suite: bare `uv run pytest` with the API_TEST_* env vars for
  the 15432 test DB; explicit arg orders now work too (92f41f3).
  Green: 473 passed, 9 skipped under three collection orders.
- Open ops: API_APP_BASE_URL still missing in prod API env;
  project-taipan-db-1 zombie container; registration,
  typed-system-settings and password-reset worktrees deletable;
  merged feat/* branches (users-table, users-admin,
  typed-system-settings) still on origin; magic-link HTML reports and
  ticket flips exist only in its worktree.
