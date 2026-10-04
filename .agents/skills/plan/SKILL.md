---
name: plan
description: Plan a feature before building it. Use when the user describes a feature to build and wants guided planning, or types /plan. Asks clarifying questions, then routes through the installed skills (grilling, domain-modeling, codebase-design, postgresql-table-design, to-spec, implement-spec, tdd, test-smell-review) to produce a module map and a first test slice.
---

# Plan

Plan one feature. Ask before you design. Route through the installed
skills; do not re-explain them.

## Rules

- Read `.agents/memory/current.md` first.
- List `.agents/skills/` before claiming a skill is missing.
- Follow `AGENTS.md`: STE100 output, `uv run` for commands,
  domain-named shareable packages.
- Ask questions before proposing anything. If the idea is fuzzy,
  use the `grilling` skill.
- Do not implement. Stop after the plan; wait for the user.

## Steps

1. **Clarify.** Restate the feature in one sentence. Ask about scope,
   constraints, and what "done" means. Max 3 questions per round.
2. **Domain.** If the feature introduces new concepts, use
   `domain-modeling` to settle names and update `GLOSSARY.md` before
   designing.
3. **Seams.** Use `codebase-design` to place the code: which domain
   package or app, what the module interface hides, where the seam
   goes.
4. **Data.** If the feature touches the schema, use
   `postgresql-table-design` and check whether a migration is needed
   (`uv run db-revision`).
5. **Spec.** For anything beyond a small change, offer `to-spec` to
   write a spec file; `implement-spec` can execute it later.
6. **Slice.** Propose the first TDD slice with `tdd`: the smallest
   test that proves the core behavior. Implementation reviews new or
   edited tests with `test-smell-review` before calling them done.

## Output

- One Mermaid diagram: the proposed module map.
- A short plan: packages touched, interfaces, migration needs, first
  test slice, the `test-smell-review` gate, open questions.
- Offer an ADR via `domain-modeling` when a non-obvious call was made.
