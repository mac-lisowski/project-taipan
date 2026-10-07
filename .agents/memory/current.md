# Current state

- Branch feat/registration-settings-gate (worktree
  /home/mac/projects/moje/project-taipan-registration): registration
  spec IMPLEMENTED plus two deepening refactors, everything in one
  uncommitted commit-in-waiting, user approved commit + push + PR to
  dev. 4 tickets done, reports in .scratch/registration/issues/.
- Feature: global system_settings KV table, registration_enabled
  default false; POST /auth/register 404 when off, neutral 204 when on;
  POST /auth/activate via auth_flow.set_password_with_token (strength
  before atomic verify, is_active gate, optional revoke); web /register
  gated per render, URL token beats the switch; owner-only PUT via
  require_system_owner; public switch-only read; nullable
  users.hashed_password with clean login fail.
- Refactors: tokens.mint_single owns the one-live-link rule (digest
  private again); auth_flow.set_password_with_token shared by
  activation and reset. Review loops: 2 rounds, 5 reviewer agents, 1
  high test pin regression + 5 minors found and fixed; verdict SHIP.
- Gates at ship: pytest 438 passed 9 skips (live Infisical), vitest
  125, next build clean, ruff clean, falsegreen clean, size/bff pass.
- Deferred: resend check-then-act race (bounded by single use), APP_NAME
  x3 (architecture candidate 3), BFF result parser unification
  (candidate 5), vitest .next exclude, users.NotFound 500 if user
  deleted between mint and activate (pre-existing shape).
- Open ops: API_APP_BASE_URL in prod API env. Test DB container on
  15432 serves this branch; remove after merge. Spec flips to
  implemented + git mv on merge (PR body notes it).
