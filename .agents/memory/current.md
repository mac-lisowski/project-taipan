# Current state

- Dev pushed through fb6c115: 34a7d97 fixes all 21 falsegreen
  findings (email suite split under the 300-LOC gate: conftest.py +
  test_send_budget.py), 1e57f54 moves bff-result-module,
  magic-link-mailer, litellm-gateway-docker into
  docs/specs/implemented/ (PRs #43, #42, #36), 92f41f3 moves shared
  test helpers into api_testsupport/email_testsupport so the suite
  collects under any pytest arg order, fb6c115 renames the email
  helpers public (make_guarded, unique_address) and dedupes table
  resets into init_tables/reset_tables.
- docs/specs/planned/ holds nats-jetstream (PR #38 open) and
  chat-surface (spec.md + spec.html written 2026-10-08, tickets not
  yet cut).
- chat-surface: full OpenUI AgentInterface adoption at /chat. BFF
  chat + threads proxies; API threads router (restStorage contract)
  and streaming completion router to LiteLLM; chat_threads +
  chat_messages tables; light palette + toggle (web is dark-only
  today); chat follows app theme. Message persistence is server side:
  restStorage has no append op, the completion run replaces stored
  history and appends the assistant row.
- One platform KMS key decided, per-tenant keys dropped:
  decisions/platform-key-only.md.
- Two new specs in docs/specs/planned/:
  platform-key-provisioning (provisioner find ops +
  scripts/provision_kms.py) and email-at-rest (email_hash blind
  index, EncryptedString email, per-row re-scope helper, boot-time
  db-encrypt-emails). Both validated by research agents; fixes
  folded in.
- Next: tickets for Spec A on a feat branch.
- Python suite: bare `uv run pytest` with the API_TEST_* env vars for
  the 15432 test DB; explicit arg orders work too (92f41f3).
  Green: 473 passed, 9 skipped under three collection orders.
- Open ops: API_APP_BASE_URL still missing in prod API env;
  project-taipan-db-1 zombie container; registration,
  typed-system-settings and password-reset worktrees deletable;
  merged feat/* branches (users-table, users-admin,
  typed-system-settings) still on origin; magic-link HTML reports and
  ticket flips exist only in its worktree.
