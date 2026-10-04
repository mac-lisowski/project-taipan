---
name: taipan-world
description: Use with eval-engineering when generating Task Specs or building evaluation Tasks for project-taipan. Contains reusable project-specific knowledge about the uv workspace, the in-repo agent, Environment recipes, and verification patterns.
---

# project-taipan World Knowledge

Read `$eval-engineering` first. Use its broad references and examples as
guidance. Use this skill for reusable knowledge about how that guidance applies
to this project.

## Start here

- Read `AGENTS.md` for workspace rules: `uv run <cmd>` for everything,
  `src/` layout, folder = package = module naming.
- Run `uv sync` then `uv run pytest` to verify the workspace before
  packaging it into an Environment.
- Existing Task Specs: `evals/support-desk/tasks/ticket-escalation/Task.md`
  (Draft).
- Existing runnable Tasks: none yet.
- The evaluated Harness is `apps/agent` (planned, not yet built):
  `uv run agent "<instruction>"`, a LangChain `create_agent` loop.

## Task Spec guidance

Two Task families are planned:

- **support-desk**: agent works a seeded SQLite ticket store plus policy
  docs. Conditions to vary: policy thresholds, escalation paths, draft vs
  sent replies, similar-looking tickets.
- **task-runner**: agent transforms or reports on workspace files.
  Conditions to vary: multi-file inputs, partial failures, output schemas.

Meaningful conditions beat instruction rewrites. Keep the underlying work
stable when varying difficulty.

## Environment guidance

- Container recipe: `python:3.12-slim` + uv, COPY the repo, `uv sync`.
  Fresh container per trial gives isolation by replacement; no reset needed.
- SQLite is the preferred mutable store: deterministic to seed, cheap to
  snapshot and diff for verification.
- Policy documents live in the agent-visible workspace (`policies/`).
  Rules the agent must apply belong in those docs, not in the instruction.
- Network: model provider egress only. Everything else is frozen at build.

## Verification guidance

- Independent truth sources: final SQLite state, files under `out/`,
  and snapshot diffs of non-focal rows.
- Snapshot the full relevant tables before the run; diff after for
  prohibited collateral changes.
- Prefer deterministic checks (exact status values, row counts, file
  existence). Use a bounded semantic check only for reply wording.
- Known defect pattern to avoid: verifiers that accept "agent wrote a
  reply" without checking ticket state, or that ignore `replies` rows.

## Run and audit guidance

- The agent needs a model provider key at run time via env var. Provider
  is an open human decision; do not bake a provider into Tasks.
- Keep agent timeout in `task.toml`; a hung agent is an invalid run, not
  a scored failure.

## Existing Task coverage

- `evals/support-desk/tasks/ticket-escalation/` (Draft): policy-threshold
  escalation, draft-vs-sent reply rule, collateral-change checks.

## Known limits and open questions

- Harbor CLI is not installed. Required before any run.
- `apps/agent` is not built. Task Specs describe the planned Harness.
- Model provider and LangSmith tracing are undecided.
- `.video_agent/` at repo root is unexplored; check before assuming it is
  unrelated to evals.

## Update this skill

While designing, building, and auditing each Task:

1. Identify knowledge that will help create or build another Task.
2. Support it with repository evidence, traces, a human decision, or Task
   evidence.
3. Keep Task-specific setup and expected results in the collocated `Task.md`.
4. Put short, commonly needed guidance here.
5. Put detailed conditional guidance in a directly routed reference.
6. Add scripts, assets, and tests only when they are reusable.
7. Remove or revise guidance contradicted by later evidence.
8. Reconcile these changes with the human after the Task audit.
