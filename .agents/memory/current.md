# Current state

- Branch: `setup-wizard` (from dev). api-dev entry committed here; tickets stay in gitignored .scratch. No push until user approves.
- Tickets: 6 in `.scratch/setup-wizard/issues/` (01 roles, 02 setup API, 03 gated users, 04 test rebase, 05 web gate, 06 account). All ready-for-agent.
- Done: `api-dev` reload entry plus `watchfiles` in api dev group. Both entries read HOST (default 0.0.0.0); api-dev also reads PORT (default 8000). Vars documented in .env.example. Reload plus HOST/PORT verified on 8129. Prod uvicorn path unchanged.
- Next: ticket 01 roles foundation on this branch.
- Note: ports 8000 and 8123 already serve long-lived API processes. Left running. New dev server used 8129 for the smoke test, then stopped.
- Spec: `docs/specs/planned/setup-wizard/spec.md` (planned). Design: probe plus single-shot POST setup, register removed, require_admin gates users router, account page.
- Test state: api 77 passed / 2 skips. Web vitest 68/68.
- Trap: test DB with unknown tables breaks conftest drop_all. Fix is DROP SCHEMA public CASCADE plus recreate.
Activity mode: implement. Set when the phase changes: bash .agents/hooks/agent-mode.sh set <plan|implement|test|review|debug|docs|commit> (AGENTS.md rule 10).
