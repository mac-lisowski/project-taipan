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
- docs/specs/planned/ holds nats-jetstream (PR #38 open), chat-surface
  (implemented, move pending), email-at-rest, platform-key-provisioning
  (done on feat/chat-surface, move pending), split-screen (to-tickets
  is the next step before implementation).
- Next: to-tickets for split-screen, Spec B (email-at-rest). Local
  branch feat/users-list-ssr and origin copy now deletable.
- Open ops: API_APP_BASE_URL still missing in prod API env;
  project-taipan-db-1 zombie container; registration,
  typed-system-settings and password-reset worktrees deletable;
  merged feat/* branches (users-table, users-admin,
  typed-system-settings) still on origin.
