# Current state

- Dev has two unpushed cleanup commits: 34a7d97 fixes all 21
  falsegreen findings (email suite split under the 300-LOC gate:
  conftest.py + test_send_budget.py) and 1e57f54 moves
  bff-result-module, magic-link-mailer, litellm-gateway-docker into
  docs/specs/implemented/ with Status lines (PRs #43, #42, #36).
- docs/specs/planned/ now holds only nats-jetstream (PR #38 open).
- Python suite: run bare `uv run pytest` with the API_TEST_* env vars
  for the 15432 test DB. Explicit args like `pytest packages
  apps/api` break collection (learnings/pytest-arg-conftest-collision.md).
  Green today: 473 passed, 9 skipped.
- Open ops: push of the two dev commits is the user's call;
  API_APP_BASE_URL still missing in prod API env; project-taipan-db-1
  zombie container; registration, typed-system-settings and
  password-reset worktrees deletable; merged feat/* branches
  (users-table, users-admin, typed-system-settings) still on origin;
  magic-link HTML reports and ticket flips exist only in its
  worktree.
