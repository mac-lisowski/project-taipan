# Current state

- Branch: `feat/password-change` (off dev e989120). NO COMMITS YET:
  user gates commit and push until approval. No worktrees.
- Password change feature complete; spec MOVED to
  docs/specs/implemented/password-change/ (Status: implemented).
- api/password_change/: domain module (ticket 01), POST
  /api/account/password (02): wrong current 401, weak/same-as-old/
  mismatch 422, signed-out 401. Load-bearing bool
  REVOKE_OTHER_SESSIONS: revoke all + re-mint for caller, outcome
  reported. Notice mail best-effort (notice.py, noqa BLE001).
  PASSWORD_CHANGE template in packages/email (per-template required
  fields).
- Web (03): account form; strength bar display-only; errors verbatim;
  outcome note. FOLLOW-UP DONE: submitAuth widened to carry parsed
  success body ({ok:true; data:unknown} | error); changePassword now
  delegates to it (fork deleted). Component still owns pending/error
  state (hook does not fit note+mismatch flow).
- Second review round (2 agents: standards+design, spec+test-smell):
  no blockers. ExplodingSender given real send signature. Accepted
  calls: 401 wrong-current (ticket-pinned), hand-mirror length rule,
  outcomeNote(False) branch, _TemplateData link nullable.
- Gates green: workspace 360 passed 9 skipped (default order),
  web vitest 135, eslint/tsc/ruff, file-size/bff/docker, falsegreen
  all clean. Stamp 55efbc7e24e852bf current; edits invalidate it.
- GOTCHA: apps-before-packages pytest order breaks email log test
  (alembic fileConfig disables loggers). Default testpaths order safe.
- Next: on approval, commit (feat(password-change): ...), add PR
  number to spec Status line, then per-ticket HTML reports + ticket
  status flips in the merge flow.
