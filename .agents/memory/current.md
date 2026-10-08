# Current state

- Worktree project-taipan-chat-queued-messages, branch
  feat/chat-queued-messages: both tickets implemented, uncommitted.
  API: chat_queued_messages table (migration 1e8aa4dfa422 off
  7f7c0b2d3a74), api/chat/queue.py, four /api/threads/queue/* routes,
  cap 10, owner-scoped. Web: chat-queue.ts store + use-chat-queue
  hook, Mode C ChatComposer (hand-rolled starters), QueueChips,
  QueueDispatch in slots.rest. Review fixes applied: row deletes at
  run start via text-matched noteRunStarted (not at settle), enqueue
  returns bool for draft clearing, enqueue/hydrate guard stale
  thread replies, createdAt is a number. Next: gates, stamp, commit,
  PR to dev.
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
  chat-surface (implemented on this branch; spec moves to
  implemented/ at merge).
- chat-surface IMPLEMENTED on feat/chat-surface (tickets 01-05 done,
  reports in .scratch/chat-surface/issues/): full OpenUI
  AgentInterface at /chat (pinned 0.17.0/0.3.1 exact); BFF chat
  (300s stream relay) + threads proxies; API threads router
  (restStorage contract) + /api/chat/complete streaming from
  LiteLLM; chat_threads + chat_messages (migration 7f7c0b2d3a74);
  server-side history replace per run + assistant append at close,
  partial on abort; light palette + toggle, chat follows app mode.
  Four two-axis review rounds. Round 2 key bug: the OpenUI adapter
  silently drops SSE error payloads, so pre-stream gateway failure
  answers 502 (SDK shows thread error); mid-stream keeps the SSE
  event. Suites: 505 pytest (2 skipped), 216 vitest, build + all
  gates green. Live smoke blocked: LiteLLM has zero models
  registered (ops: register one, set API_CHAT_MODEL to match).
- One platform KMS key decided, per-tenant keys dropped:
  decisions/platform-key-only.md.
- Two new specs in docs/specs/planned/:
  platform-key-provisioning (provisioner find ops +
  scripts/provision_kms.py) and email-at-rest (email_hash blind
  index, EncryptedString email, per-row re-scope helper, boot-time
  db-encrypt-emails). Both validated by research agents; fixes
  folded in.
- Spec A (platform-key-provisioning) DONE on feat/chat-surface
  (commit 6fe08bc amended): find ops + hardened create,
  ensure_project/ensure_key with Ensured(id, created), cause-matched
  verify hints, typed KmsError.status_code, scripts/provision_kms.py
  (root dev-group kms dep), docs swapped. 4 subagent review rounds,
  all findings fixed. kms suite: 48 passed, 0 skipped with live
  stack. Gotchas: testsupport.py name collided with crypto's (now
  kms_testsupport.py); pre-push pytest failed on the parallel
  session's in-flight chat tests until they settled.
- PR #46 open (feat/chat-surface to dev); branch also carries the
  parallel session's chat surface implementation.
- Next: merge PR #46; Spec B (email-at-rest) is queued after it.
- Python suite: bare `uv run pytest` with the API_TEST_* env vars for
  the 15432 test DB; explicit arg orders work too (92f41f3).
  Green: 473 passed, 9 skipped under three collection orders.
- Open ops: API_APP_BASE_URL still missing in prod API env;
  project-taipan-db-1 zombie container; registration,
  typed-system-settings and password-reset worktrees deletable;
  merged feat/* branches (users-table, users-admin,
  typed-system-settings) still on origin; magic-link HTML reports and
  ticket flips exist only in its worktree.
