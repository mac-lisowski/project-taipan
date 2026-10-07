# Current state

- Branch: `feat/tenant-scoped-roles` (based on dev 3fd6054; spec files
  restored into the tree from `docs/tenant-scoped-roles` 5189bb3, staged).
- Tenant-scoped roles IMPLEMENTED, ALL UNCOMMITTED. Tickets 01-05 done by
  subagents, no commits per user gate. Working tree = the whole feature:
  2 new models (user_tenant_role, user_system_role + SystemRole enum,
  shared allowed_roles_sql helper in user_role.py), migrations
  f57a78ef14d6 (expand + backfill) and 12cb7ee20e8d (drop user_roles,
  copy-back downgrade), service dual-write then old writes removed, authz
  reads new tables only (roles_for deleted), /me adds system_roles, web
  Me type + fixtures + account page renders system roles apart; owner-only sidebar system section + mock /settings page.
- Verification: root pytest 375 passed 9 skipped; web vitest 135; tsc
  clean; ruff clean. code-review two-axis CLEAN (fixed: shared CHECK
  helper, stale comment). test-smell-review PASS 0 findings. Subagent
  audit (3 agents): no defects, claims verified.
- LIVE DB `app` on project-taipan-db-1 (localhost:5432) UPGRADED
  e60b90cbea93 -> 12cb7ee20e8d. Real user 3 (mac@mivia.app) backfilled:
  admin+member in tenant cc137ea2..., system_owner. Read-path smoke on
  live data: principal roles/system_roles + require_admin OK. user_roles
  gone, tenant_deks intact.
- Ticket statuses in .scratch/tenant-scoped-roles/issues/ left
  ready-for-agent: done-flip needs HTML reports + stamp at commit time.
- Gotchas hit: litellm session moved dev + checked it out mid-flow (feat
  branch got cut from dev, spec restored via git restore --source); agent
  05 manually dropped stale user_roles on shared app_test DB once
  (create_all leftover blocked drop_all).
- Architecture pass DONE (code-review CLEAN + fixed shared SYSTEM_OWNER_ROLE const;
  explorer found 5 strong deepening candidates, report /tmp/architecture-review-*.html):
  implemented authz.can() point-query seam + require_system_owner (tested), deleted dead
  sessions.tenant_id_for_token, pinned /users instance-wide semantics (test + why-comment).
  DEFERRED by design (hypothetical seams, invite spec territory): membership-switch
  operation, register/provisioning split, real /users tenant scoping.
- Next: user reviews diff and commits (then stamp + HTML reports +
  status flips per rule 11/12); spec moves to implemented on merge.
