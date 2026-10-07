# Current state

- Branch: `feat/password-change` PUSHED; PR #34 open to dev
  (feat 2c9927c + two docs commits). Squash-merge like prior PRs.
- Password change feature complete; spec at
  docs/specs/implemented/password-change/ (Status: implemented).
- api/password_change/: domain module (ticket 01), POST
  /api/account/password (02): wrong current 401, weak/same-as-old/
  mismatch 422, signed-out 401. Load-bearing bool
  REVOKE_OTHER_SESSIONS: revoke all + re-mint for caller, outcome
  reported. Notice mail best-effort (notice.py, noqa BLE001).
  PASSWORD_CHANGE template in packages/email (per-template required
  fields).
- Web (03): account form; strength bar display-only; errors verbatim;
  outcome note. submitAuth widened to carry parsed success body
  ({ok:true; data:unknown} | error); changePassword delegates to it.
  Component still owns pending/error state (hook does not fit
  note+mismatch flow).
- Two review rounds clean (code-review two-axis, then standards+design
  and spec+test-smell agents). Accepted calls: 401 wrong-current
  (ticket-pinned), hand-mirror length rule, outcomeNote(False) branch,
  _TemplateData link nullable.
- Gates green at commit: workspace 360 passed 9 skipped (default
  order), web vitest 135, eslint/tsc/ruff, file-size/bff/docker,
  falsegreen all clean.
- GOTCHA: apps-before-packages pytest order breaks email log test
  (alembic fileConfig disables loggers). Default testpaths order safe.
- Next: at merge, squash + add PR number to spec Status line;
  per-ticket HTML reports + ticket status flips in the merge flow.
  Follow-up candidate: fold form pending/error into useAuthSubmit.
