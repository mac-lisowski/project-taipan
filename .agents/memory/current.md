# Current state

- Users admin COMMITTED on feat/users-admin (b4b7944, rebased onto
  dev 7e462de). Awaiting PR + user review. Spec moves to
  docs/specs/implemented/ with the PR number. Tickets in
  .scratch/users-admin/issues/ are done with reports.
- Feature: users routes owner-guarded; PUT activation with revoke-all
  + self/last-owner 409s; principal rejects missing/inactive users;
  detail joins profile/roles/tenants; delete removes the personal
  tenant and its DEK; activation+reset dead links answer 400;
  profiles session+self-only; web /users/[id] detail page.
- Dev since 919f779: PR #41 typed settings (74be3b3), PR #42 link
  mail module (644294f), PR #43 api-result module (7e462de;
  api-detail.ts deleted, web client calls go through
  lib/api-result.ts).
- Known notes: KV activation/reset tokens survive delete until TTL
  (spec accepts); email suppressions stay on delete.
- Open ops: API_APP_BASE_URL in prod API env; project-taipan-db-1
  zombie, user call; project-taipan-registration worktree removal,
  user call; feat/users-table branch deletable (squashed 919f779).
