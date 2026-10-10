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
  chat-artifacts, chat-attachments, email-at-rest, object-storage.
- object-storage IMPLEMENTED on feat/object-storage (uncommitted, not
  pushed; branch off dev). Spec: docs/specs/planned/object-storage/,
  amended during impl (chainguard/minio digest pin replaces pulled
  minio/minio+mc images, lazy bucket creation replaces mc init, list
  param is cursor not after). Eight tickets under
  .scratch/object-storage/issues/, all Status done with HTML reports.
  Built: packages/storage (ObjectStore port, S3ObjectStore minio SDK
  lazy client + ensure_bucket once per bucket, FakeObjectStore);
  api/files package (policies attachment browser/artifact
  service-only, service store_upload/store_bytes/delete, reads
  get/open/list_page keyset, lifecycle detach_user/detach_tenant +
  discard, errors, store composition root); files table migration
  3650287efea4 (scope CHECK, private-needs-uploader CHECK, RESTRICT
  uploader, unique bucket+key, partial tenant index); /api/files five
  session routes + ASGI byte-count middleware; users.remove takes
  store (bucket param dropped post-review, row.bucket is truth);
  MinIO in both compose files. Two review rounds: r1 fixed 9
  (transport errors past StorageError, bucket data clump, unscoped
  private deletes, metadata GET hitting S3, __enter__ dunders, dup
  discard/CHUNK_BYTES, 300 LOC split listing.py -> reads.py +
  errors.py); r2 fixed 3 (visible rename, discard moved into
  lifecycle.py to keep users.service FastAPI-free, hardcoded test
  bucket). Gates: 677 pytest + 12 skipped (3 stable runs), 532 api,
  28 storage with live MinIO leg, ruff/format/size/bff/docker green,
  falsegreen + test-smell clean. Gotchas: parallel api test agents
  need own app_test_aNN DB (conftest DROP SCHEMA per session);
  full-suite flake earlier was a shared-DB collision, not a bug;
  project-taipan-minio-1 left running on 9000/9001 for the live leg;
  an earlier agent ran `compose down -v` and wiped the stopped
  project-taipan stack's volumes (running mivia-* untouched).
  Next: commit + push when user asks; then chat-artifacts and
  chat-attachments consumers land on api.files.
- split-screen spec amended post-review (per-instance queue/model
  stores, users-view BFF adapter, /system/settings path, third
  nav-conversion site, DOM smoke test resolves the no-DOM-test
  contradiction) and ticketed: .scratch/split-screen/issues/01-06
  (pane-state -> nav + stores -> shell -> contents -> entry points).
  Ticket review caught + fixed: missing singleton consumers
  (use-chat-queue/model, inflight, shared taipan-chat-model key),
  unassigned mount-restore and affordance-hiding, 04/05 header dup,
  login needs a new next= return flow. Spec committed 6d5dccd on
  feat/split-screen. Tickets 01-06 all implemented and committed on
  that branch (latest: 0cc6783 entry points, ?pane= cross-path carry,
  proxy-stamped next= login flow verified via curl on the built
  server, happy-dom smoke test for the rest slot). PR #51 MERGED
  (squash af65709); spec moved to implemented/. b33057e had bundled
  a write-pseudocode skill; excised in 0536844 (skill files +
  AGENTS.md rule 15 + skill wirings reverted).
- Next: commit object-storage when asked, or Spec B (email-at-rest);
  chat-artifacts/chat-attachments consumers come after storage lands.
  feat/users-list-ssr and feat/split-screen deletable locally and on origin.
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
