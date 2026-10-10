# Current state

- chat-files MERGED to dev (PR #53 squash cd6338c). Both specs moved to
  docs/specs/implemented/ with Status flipped. Final fix round added
  resolveArtifactId (content-match disambiguation for same-title/type
  duplicates, replaces findArtifactSummary first-hit) +
  use-stored-artifact-id.ts hook, and mobile artifact access via
  globals.css (workspace toggle resurfaced as floating button since the
  SDK hides the whole thread header on mobile; workspace rail widened
  294px -> 100%; detailed view already covers inset:0).
- chat-files extras on feat/chat-files (PR #53): Workspace slot mounted
  on both chat surfaces (per-thread artifact rail, header toggle auto-
  appears); GET /api/artifacts/{id}/download streams .md (documents) /
  .csv (tables) via api/artifacts/download.py; Download button in
  ArtifactActual resolves stored id from canonical path or
  findArtifactSummary(threadId+title+type) off-path. DOCUMENT_TYPE/
  TABLE_TYPE constants moved to artifacts.service (tools.py aliases).
  View tests split to components/chat/artifact-views.test.tsx (300 LOC
  cap). SYSTEM_PROMPT now tells the model about save_artifact; tool
  content arg gained anyOf [string, array<object>]. 609 api + 437 web.
- chat-files implementation COMPLETE on feat/chat-files, uncommitted
  (user said no commit/push/branch). All 8 tickets done + HTML reports
  in .scratch/chat-files/issues/. Two review rounds run on the full
  diff: r1 two-axis code-review -> fixed tool_calls leaking upstream
  on reload (complete.py prepare/_upstream_safe strips them; stored
  history keeps verbatim), mid-stream GatewayError now _persist-s the
  partial reply before error_event, files.delete IntegrityError ->
  InUse -> 409 (artifact-owned file), tools.py index-less fragment
  folding, TYPE_CHECKING Principal, SEEN_MAX=500 cap on
  artifact-storage seen map, spec amended (title-search index never
  landed; ilike can't use btree anyway). r2 verify -> 2 minors fixed:
  CompletionMessageIn null content now assistant-only
  (model_validator), _persist failure in the mid-stream branch no
  longer swallows error_event (try/except + log). Full suite 748
  passed / 15 skipped; web 432 vitest, lint, tsc green; all hard
  gates pass; falsegreen 0 high. Remaining accepted risks:
  attachments _Budget over-rejects near 200k (safe direction), share
  snapshot puts attachment lines before text.
- chat-files ticket 08 (artifacts web) DONE on feat/chat-files,
  uncommitted. New lib/artifact-storage.ts (ArtifactStorage
  {list,get,update} over /api/artifacts + deleteArtifact +
  peekArtifactSummary cache so views see threadId the parser never
  gets), lib/artifact-renderers.tsx (shared ArtifactDraft props; parser
  reads partialJSONParse args while streaming, registers meta only on
  strict-JSON closed args because ctx.isStreaming never clears without
  a tool result; meta.id = FNV-1a hash of kind+title, the call id never
  reaches the parser; two renderers share toolName save_artifact -
  first registration wins so both must handle both kinds;
  artifactSurface = defineArtifactCategories Documents+Tables spread on
  AgentInterface), components/chat/artifact-views.tsx (preview card;
  actual resolves stored id from useNav path artifacts/{cat}/{id} -
  editable there via textarea/EditableTable + save + two-tap delete,
  read-only in the in-thread detailed view; dead-thread artifacts hide
  the SDK's unconditional "Go to thread" via an inline style).
  chat-config attaches artifact storage; ArtifactNav in sidebar;
  labels tabs.artifacts/defaultCategory "Documents"; auto-open on
  (removed artifactAutoOpen={false} in chat-app + pane-chat). BFF
  /api/artifacts[[...path]] route + /artifacts[[...slug]] page for
  reload survival. Step 5 finding: openAIMessageFormat.fromApi keeps
  tool_calls verbatim - no wrapper change needed (pinned by test).
  chat-config.test.ts split at the cap: format cases moved to
  chat-config-format.test.ts. Gates: 432 vitest, lint, tsc, build,
  size, bff, unreached (git add -N on new files so git-grep sees
  untracked importers), docker, falsegreen + J1-J6 clean. HTML report
  written. No commit made.
- chat-files ticket 07 (completion tools) DONE on feat/chat-files,
  uncommitted. New api/chat/tools.py: SAVE_ARTIFACT_TOOL schema,
  ArtifactSink (store+principal+bucket), collect_calls folds
  delta.tool_calls fragments per index (name+arguments concatenated),
  save_calls maps args to {"markdown"|"rows"} bodies and calls
  artifacts.create per call (malformed/wrong-shape args warn+skip,
  create failure logs+continues). gateway.stream gained tools +
  tool_choice kwargs (tool_choice only rides with tools). complete.py
  stream_reply takes optional sink; _persist appends assistant message
  when text OR calls exist, stores verbatim tool_calls, commits, then
  saves artifacts after the commit so upsert failure can't cost
  history. routers/chat.py wires tools under function_calling,
  tool_choice=auto under tool_choice, sink only when tools advertised.
  Tests: test_chat_tools.py (11) + 3 gateway tests; FakeGateway records
  tools/tool_choices. Gates: 603 pytest + 2 skip on app_test_a07, ruff,
  size, falsegreen + J1-J6 clean. Ticket Status done, HTML report
  written. No commit made.
- chat-files ticket 02 (attachment resolution) DONE on feat/chat-files,
  uncommitted. New api/chat/attachments.py resolve_parts maps user
  binary parts per model flags (image+vision->image_url data URL,
  pdf+pdf_input->file part, pdf->pypdf text, text/plain->text, else
  marker); complete.py gained MAX_BINARY_PARTS=5 (checked in validate)
  + MAX_RESOLVED_BYTES=20MiB (charged in resolver _Budget with a 200k
  text allowance); routers/chat.py resolves flags via
  catalog.capabilities(model or default) and sends resolved copies to
  the gateway while history keeps parts verbatim; shares._snapshot
  flattens binary parts (create_or_refresh takes store kwarg, snapshot
  resolves as thread owner via synthetic Principal; is_shared/read_
  snapshot unchanged); ChatMessageIn.content str|list; _derive_title
  reads first text part. pypdf added to api deps + lockfile. Tests:
  test_chat_attachments.py + test_chat_attachments_http.py (18 tests,
  split for the 300-LOC gate, deterministic uuids for falsegreen).
  Gates: 588 pytest + 2 skip on app_test_a02, ruff, size, falsegreen
  green. Ticket Status done, HTML report written. No commit made.
  Deviation: dropped the sketched bucket param (row.bucket is truth).
- chat-files ticket 01 (model capabilities) DONE on feat/chat-files,
  uncommitted, shared worktree with parallel agents on tickets 02-08.
  ModelCatalog fetches /model/info beside /v1/models per TTL window;
  entries carry vision/pdf_input/function_calling/tool_choice, non-chat
  mode filtered, capabilities(model_id) accessor added; ChatModel type
  gained the two optional flags. Fail closed on info, fail open on
  listing (a failed info refetch re-lists filtered deployments for one
  window). New apps/api/tests/chat/ subdir; api_testsupport imports
  work via the parent conftest (see learnings). Gates green: 543 pytest
  + 2 skip (parallel agent's TDD-red test_artifacts_service.py excluded
  from full-suite runs - it breaks collection), 37 vitest, ruff, size,
  bff, falsegreen. Ran with API_TEST_URL=.../app_test_a01 plus
  API_TEST_ADMIN_URL (conftest wants both). Ticket Status done, HTML
  report written. No commit made.
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
  chat-artifacts, chat-attachments, email-at-rest. Both chat specs
  revised to final form (no phased deferrals): attachments are
  files-registry-backed taipan_file parts with vision gating via
  /model/info; artifacts persist tool_calls, edit+delete in the
  workspace, and survive thread delete via SET NULL.
- object-storage MERGED to dev (PR #52). Spec moved to
  docs/specs/implemented/object-storage/ with Status flipped,
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
- Branch: feat/nats-jetstream (PR #38 open), rebased onto dev after the
  storage/chat-files merges. NATS JetStream spec IMPLEMENTED. 8 tickets
  in .scratch/nats-jetstream/issues/ with HTML reports.
- Feature: packages/messaging (seam.py Message/Messaging/MessagingError +
  subject grammar + define_stream; fake.py FakeBroker; nats.py NatsBroker
  lazy bounded connect + durable pull consumers; nats_streams.py StreamOps
  mixin replay/ensure_stream). MsgConfig 6th frozen group: API_BROKER_URL
  (nats://localhost:4222) + API_JETSTREAM_STORE (file|memory, per-stream
  StreamConfig.storage). Factory build_messaging defaults NatsBroker,
  FakeBroker explicit. GET /health at root reports broker.connected
  (cached only, no ping). Compose nats in both stacks (nats:2.15-alpine,
  docker/nats/nats.conf, volumes, ports 4222/8222/1883 host only).
  Railway: docker/nats/Dockerfile + nats-railway.conf (no MQTT).
  docs/messaging.md + commit-convention.md regenerated (messaging scope).
- Verification: root pytest 470 passed 10 skipped (live nats tier RUNS
  against compose broker on 4222; 1 paho skip). ruff clean; falsegreen
  0 high 3 low C16 (uuid namespace convention). code-review two-axis
  CLEAN after repair round (6 fixes: vocab single-sourced in messaging
  STORE_MODES/RETENTIONS, fake replay wildcard membership bug, headers
  field dropped, dead_letter required kwarg, live-test conftest dedup,
  stale docstring). httpx2 + pyyaml added to apps/api deps.
- Rebase note: additive conflicts in config/main/routers/schemas/pyprojects
  (union both sides), uv.lock regenerated via `uv lock`, compose keeps
  nats+minio services and both volumes.
- Compose broker project-taipan-nats-jetstream-nats-1 intentionally left
  RUNNING (healthy) on 4222/8222/1883 from the worktree stack; live
  tests use it. Stop with docker compose -f docker-compose.yaml down
  (keeps natsdata volume).
- Gotchas: nats-py has no retry_on_failed_connect (initial connect
  blocks; bounded wait_for + background-at-first-use pattern); JetStream
  DLQ is app-level (metadata num_delivered >= cap, then publish + term);
  replay = ordered consumer with quiet-window end; member dev groups
  (paho) do not install under root uv run (use uv run --with paho-mqtt).
- Next: spec moves to docs/specs/implemented/nats-jetstream/ at merge
  (git mv + PR status line per implement-spec). Real job types and event
  schemas are the follow-up spec; edge bridging stays off.
