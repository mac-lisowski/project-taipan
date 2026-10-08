# Current state

- Queued chat messages MERGED to dev (PR #47 squash d351e3a):
  chat_queued_messages table (migration 1e8aa4dfa422 off
  7f7c0b2d3a74), api/chat/queue.py, four /api/threads/queue/* routes,
  cap 10, owner-scoped. Web: chat-queue.ts store + use-chat-queue
  hook, Mode C ChatComposer (hand-rolled starters), QueueChips,
  QueueDispatch in slots.rest. Review fixes included: row deletes at
  run start via text-matched noteRunStarted (not at settle), enqueue
  returns bool for draft clearing, enqueue/hydrate guard stale
  thread replies, createdAt is a number. Worktree
  project-taipan-chat-queued-messages and branch
  feat/chat-queued-messages now deletable.
- chat-model-switcher MERGED to dev (PR #48 squash 0966916):
  ModelCatalog caches LiteLLM /v1/models behind
  API_CHAT_MODELS_TTL_SECONDS (60s); GET /api/chat/models serves
  [{id, name, default?}]; complete validates optional body model
  against the same set (422 unknown, absent keeps chat_model); web
  switcher in ThreadHeader persists taipan-chat-model; BFF catch-all
  relayed the route (test only). Worktree
  project-taipan-chat-model-switcher and branch
  feat/chat-model-switcher now deletable.
- Composer/queue/mermaid follow-up fixes on dev: the custom Mode C
  composer now uses one toggle button (stop replaces send while
  running, SDK pattern); QueueChips moved inside the composer
  container (the SDK slot div is unstyled, so bare children sat
  flush left) and restyled as a numbered scrolling stack panel;
  assistant ```mermaid fences render via the mermaid package
  (pre-level component override, 250ms stream debounce,
  suppressErrorRendering, raw-source fallback while parsing fails).
- Latest dev work: fixes all 21 falsegreen findings (email suite
  split under the 300-LOC gate: conftest.py + test_send_budget.py),
  moves bff-result-module, magic-link-mailer, litellm-gateway-docker
  into docs/specs/implemented/ (PRs #43, #42, #36), moves shared
  test helpers into api_testsupport/email_testsupport so the suite
  collects under any pytest arg order, renames the email helpers
  public (make_guarded, unique_address) and dedupes table resets
  into init_tables/reset_tables.
- docs/specs/planned/ holds nats-jetstream (PR #38 open),
  chat-surface (implemented, move pending), email-at-rest, and
  platform-key-provisioning (done on feat/chat-surface, move
  pending) and now split-screen.
- chat-surface IMPLEMENTED and merged to dev (PR #46): full OpenUI
  AgentInterface at /chat (pinned 0.17.0/0.3.1 exact); BFF chat
  (300s stream relay) + threads proxies; API threads router
  (restStorage contract) + /api/chat/complete streaming from
  LiteLLM; chat_threads + chat_messages (migration 7f7c0b2d3a74);
  server-side history replace per run + assistant append at close,
  partial on abort; light palette + toggle, chat follows app mode.
  Every private page now mounts ChatApp; app views render as
  AgentInterface.Route children, so chat and page are mutually
  exclusive today. Round 2 key bug: the OpenUI adapter silently
  drops SSE error payloads, so pre-stream gateway failure answers
  502 (SDK shows thread error); mid-stream keeps the SSE event.
  Live smoke blocked: LiteLLM has zero models registered (ops:
  register one, set API_CHAT_MODEL to match).
- One platform KMS key decided, per-tenant keys dropped:
  decisions/platform-key-only.md.
- Spec A (platform-key-provisioning) DONE on feat/chat-surface:
  find ops + hardened create, ensure_project/ensure_key with
  Ensured(id, created), cause-matched verify hints, typed
  KmsError.status_code, scripts/provision_kms.py (root dev-group
  kms dep), docs swapped. kms suite: 48 passed with live stack.
  Gotchas: testsupport.py name collided with crypto's (now
  kms_testsupport.py); pre-push pytest failed on a parallel
  session's in-flight chat tests until they settled.
- Split-screen spec WRITTEN at docs/specs/planned/split-screen/
  (spec.md + spec.html), two-axis reviewed: one AgentInterface +
  a slots.rest right pane (persistent flex sibling, custom drag
  separator, ?pane= URL param, nested AgentInterface for pane
  chat, app-owned shell-nav abstraction per surface). SDK
  DetailedViewPanel is the documented fallback. SDK findings
  logged in learnings/openui-sdk-pane-hooks.md. Tickets not yet
  generated; to-tickets is the next step before implementation.
- Next: to-tickets for split-screen; Spec B (email-at-rest)
  queued.
- Python suite: bare `uv run pytest` with the API_TEST_* env vars
  for the 15432 test DB; explicit arg orders work too.
  Green: 473 passed, 9 skipped under three collection orders.
- Open ops: API_APP_BASE_URL still missing in prod API env;
  project-taipan-db-1 zombie container; registration,
  typed-system-settings and password-reset worktrees deletable;
  merged feat/* branches (users-table, users-admin,
  typed-system-settings) still on origin; magic-link HTML reports
  and ticket flips exist only in its worktree.
