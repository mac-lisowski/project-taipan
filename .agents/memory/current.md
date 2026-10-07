# Current state

- Branch: `dev` at `3f8b444` (PR #32 merged; feature branch merged).
- Candidate 5 reversed by user: double resolve is FIXED, not accepted.
  ADR-0002 deleted. `sessions` stashes the middleware resolve on
  `request.state` (token-bound); `authz.resolve_session` reuses it.
  4 KV gets down to 2 per authed request.
  Test: `apps/api/tests/test_resolve_once.py` (3 tests, red first).
  Gates: api suite 245 passed 2 skipped, ruff clean, falsegreen clean.
- Live run 2026-10-07 16:19: full workspace 314 passed ZERO skips
  (token live), web vitest 15 files 121 passed.
- Candidate 3 (seam discipline) still UNCOMMITTED: `set_token_store`
  deleted, why-comment on session setter.
- Next: review/stamp/commit the combined uncommitted diff.
