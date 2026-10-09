---
name: to-tickets
description: Break a plan, spec, or the current conversation into a set of tracer-bullet tickets, each declaring its blocking edges, saved as one file per ticket next to the spec.
disable-model-invocation: true
---

# To Tickets

Break a plan, spec, or conversation into a set of **tickets**: tracer-bullet vertical slices, each declaring the tickets that **block** it.

Tickets are local files, not issue tracker entries: one file per
ticket under `.scratch/<feature-slug>/issues/<NN>-<slug>.md`.
`.scratch/` is gitignored - tickets are working state, specs in
`docs/specs/planned/` (open) and `docs/specs/implemented/` (shipped)
are the durable artifacts.

A done ticket gets an HTML change report beside it, same basename:
`.scratch/<feature-slug>/issues/<NN>-<slug>.html`. The implement-spec
merger writes it from the merged diff before Status flips to done;
the ticket template carries the checkbox.

Note: file-writing tools refuse paths under `.scratch/` (gitignored).
Write ticket files via the shell instead (e.g. a heredoc).

## Process

### 1. Gather context

Work from whatever is already in the conversation context. If the user passes a reference (a spec path, an issue number or URL) as an argument, fetch it and read its full body and comments.

### 2. Explore the codebase (optional)

If you have not already explored the codebase, do so to understand the current state of the code. Ticket titles and descriptions should use the project's domain glossary vocabulary, and respect ADRs in the area you're touching.

Look for opportunities to prefactor the code to make the implementation easier. "Make the change easy, then make the easy change."

### 3. Draft vertical slices

Break the work into **tracer bullet** tickets. Each ticket carries
enough detail to land in a fresh context: context pointers, an ordered
implementation plan, the failing tests to write first, the gates it
must pass, and checkable acceptance criteria.

<vertical-slice-rules>

- Each slice cuts a narrow but COMPLETE path through every layer (schema, API, UI, tests): vertical, NOT a horizontal slice of one layer
- A completed slice is demoable or verifiable on its own
- Each slice is sized to fit in a single fresh context window
- Any prefactoring should be done first

</vertical-slice-rules>

Give each ticket its **blocking edges**: the other tickets that must complete before it can start. A ticket with no blockers can start immediately.

**Wide refactors are the exception to vertical slicing.** A **wide refactor** is one mechanical change (rename a column, retype a shared symbol) whose **blast radius** fans across the whole codebase, so a single edit breaks thousands of call sites at once and no vertical slice can land green. Don't force it into a tracer bullet; sequence it as **expand–contract**. First expand: add the new form beside the old so nothing breaks. Then migrate the call sites over in batches sized by blast radius (per package, per directory), each batch its own ticket blocked by the expand, keeping CI green batch to batch because the old form still exists. Finally contract: delete the old form once no caller remains, in a ticket blocked by every migrate batch. When even the batches can't stay green alone, keep the sequence but let them share an integration branch that all block a final integrate-and-verify ticket; green is promised only there.

### 4. Quiz the user

Present the proposed breakdown as a numbered list. For each ticket, show:

- **Title**: short descriptive name
- **Blocked by**: which other tickets (if any) must complete first
- **What it delivers**: the end-to-end behaviour this ticket makes work

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the blocking edges correct: does each ticket only depend on tickets that genuinely gate it?
- Should any tickets be merged or split further?

Iterate until the user approves the breakdown.

### 5. Write the ticket files

Write one file per ticket under
`.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01` in
dependency order (blockers first). Each file's "Blocked by" lists the
numbers/titles it depends on. Use the per-ticket file template below:
one ticket per file, never a single combined file.

Work the **frontier**: any ticket whose blockers are all done. For a purely linear chain that means top to bottom.

Do NOT close or modify any parent issue.

<ticket-template>

# <NN>: <Ticket title>

**Status:** ready-for-agent | in-progress | done
**Blocked by:** the numbers/titles of the tickets that gate this one, or "None (can start immediately)".
**Parallel with:** the ticket numbers that can be worked at the same
time as this one (no blocking edge in either direction, no file
overlap). Helps schedulers and humans run the frontier without
inverting the graph.
**Conflicts with:** ticket numbers touching the same files. Not
derivable from blocking edges - two unblocked tickets editing the
same file serialize anyway.

## What to build

The end-to-end behaviour this ticket makes work, from the user's
perspective, not a layer-by-layer implementation list.

**Out of scope:** one line naming adjacent work this ticket must not
absorb.

## Context pointers

- Spec: `docs/specs/planned/<slug>/spec.md` (sections that bind this ticket)
- Prior art: files that already show the pattern to copy
- Decisions: the spec/ADR lines that constrain the shape

A fresh-context implementer must be able to start from pointers alone.

## Implementation plan

Ordered steps naming the modules to create or modify and the wiring
they need (dependencies, env vars, registrations). Sketch interfaces
only where the spec pins them; otherwise name the shape. Pin
control-flow-heavy logic as pseudocode per `write-pseudocode`.

## Tests (TDD)

The failing tests to write before implementing, named and with the
observable behaviour each asserts. Implementer runs the `tdd` skill:
red first, then green. For non-code tickets (docs, config), write
"N/A" and name the mechanical verification instead: a command that
fails before the change and passes after.

## Gates

- `uv run pytest <test files>`
- `uv run ruff check` and `uv run ruff format --check` on touched files
- `uvx falsegreen <test files>`, then a `test-smell-review` pass
- every hard gate that matches touched file types:
  `scripts/check-file-size.sh`, `scripts/check-bff.sh`,
  `scripts/check-docker.sh`, `scripts/check-commit-msg.sh`
- `code-review` skill on the diff, then
  `bash .agents/hooks/review-stamp.sh` before `git commit`

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2

## Definition of done

Uniform across tickets; checked before Status flips to done.
Enforced: `review-stamp.sh` refuses to stamp while a done ticket has
unchecked boxes, and code-review's Spec axis verdicts every item
against the diff.

- [ ] Every acceptance criterion checked
- [ ] Tests written red-first (tdd), all pass
- [ ] All gates green (pytest, ruff, falsegreen + test-smell-review,
      file-size cap)
- [ ] code-review pass on the diff is clean, review stamped before
      commit
- [ ] Report written: `<NN>-<slug>.html` next to this ticket file
      (the implement-spec merger writes it from the merged diff)
- [ ] Ticket file Status updated to `done`; `.agents/memory/current.md`
      updated if repo state changed
- [ ] No leftover artifacts (test resources, temp files, stray env)

</ticket-template>

Avoid specific file paths or code snippets in tickets: they go stale fast. Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it and note briefly that it came from a prototype. Trim to the decision-rich parts, not a working demo, just the important bits. Pseudocode per the `write-pseudocode` skill is likewise allowed wherever control flow is the decision.
