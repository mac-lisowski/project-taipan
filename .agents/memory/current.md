# Current state

- users-list-ssr MERGED to dev (PR #50 squash 9b748af); spec in
  docs/specs/implemented/users-list-ssr/ with Status flipped. Spec
  review commit e01d327; q-trim contract line added during review. API:
  GET /api/users answers UserPageOut via new api/users/listing.py
  (q ilike escaped+trimmed, status, page clamp, page_size 10/25/50;
  flat list body removed with its service fn and four test files
  rewritten). Web: /users server page parses URL (q,status,page,size,
  user), fetches one page with session cookie, table drives controls
  through the URL; threads seed one server cursor page via a
  shell-owned ChatStorage wrapper (consumed once per page load);
  settings switch reads per render with client-fetch fallback;
  account/overview already SSR. syncUrl keeps query on same-path.
  Five review rounds; catches: check-bff single-untracked-file scan
  needed -H (behavior fix), SDK sidebar fires onNavigate not
  ChatSidebarContents openPath, seed replay on remount, stale flush
  closures. Gates: 584 API (12 skip) on the 15432 container, 250
  vitest, build, ruff, 3 hard gates green.
- Python suite on this branch: 584 passed, 12 skipped with
  API_TEST_URL/API_TEST_ADMIN_URL pinned to the 15432 test container
  (taipan-password-reset-test-db, reused and still up).
- Web suite: 250 vitest; upstream.test.ts split at the 300-LOC gate
  (new upstream-users.test.ts).
- Spec moves to implemented/: chat-surface + platform-key-provisioning
  (PR #46), chat-queued-messages (PR #47), chat-model-switcher
  (PR #48), chat-thread-sharing (PR #49). Status lines flipped;
  email-at-rest link to platform-key-provisioning repointed.
  docs/specs/planned/ now holds nats-jetstream (PR #38 open),
  chat-artifacts, chat-attachments, email-at-rest, split-screen
  (to-tickets is the next step before implementation).
- split-screen spec amended post-review (per-instance queue/model
  stores, users-view BFF adapter, /system/settings path, third
  nav-conversion site, DOM smoke test resolves the no-DOM-test
  contradiction) and ticketed: .scratch/split-screen/issues/01-06
  (pane-state -> nav + stores -> shell -> contents -> entry points).
  Ticket review caught + fixed: missing singleton consumers
  (use-chat-queue/model, inflight, shared taipan-chat-model key),
  unassigned mount-restore and affordance-hiding, 04/05 header dup,
  login needs a new next= return flow. UNCOMMITTED spec edits on dev.
- Next: implement split-screen (or commit spec first), Spec B
  (email-at-rest). feat/users-list-ssr deleted locally and on origin.
- Open ops: API_APP_BASE_URL still missing in prod API env;
  project-taipan-db-1 zombie container; registration,
  typed-system-settings and password-reset worktrees deletable;
  merged feat/* branches (users-table, users-admin,
  typed-system-settings, chat-thread-sharing) still on origin; magic-link HTML reports and
  ticket flips exist only in its worktree.
- chat-thread-sharing MERGED to dev (PR #49 squash f91699d); spec
  moved to docs/specs/implemented/chat-thread-sharing/ with Status
  flipped (dev commits 26977c4 + memory 9c4baed). chat_thread_shares
  extension table + migration 706345e37b27 (partial unique index on
  live share per thread); POST/DELETE/GET-status under
  /api/threads/shares/* (session, owner+tenant scoped) + public
  GET /api/public/threads/{token} returning title+messages only.
  Token = base64url(HMAC_SHA256(API_SHARE_TOKEN_SECRET, share_id)) -
  spec's random token + hash-only contradicts same-URL-on-repeat-create;
  deterministic derivation resolves it; only sha256 stored. Per-process
  random fallback warns once; prod must set the env var. Web: ShareThread
  + confirm-gated revoke IconButton in ThreadHeader + MobileHeader
  actions; /share/[token] public server page (noindex header + meta);
  snapshot drops system rows and message extra keys. shares/get status
  endpoint added so revoke is reachable cross-session. Controls share
  one module store (lib/share-state.ts) since both header slots mount a
  copy. Worktree pruned: .scratch tickets + HTML reports went with it.
  473 pytest + 280 vitest green at merge time.
