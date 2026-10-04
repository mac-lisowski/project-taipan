---
name: implement-spec
description: "Implement the result of /to-spec and /to-tickets in code."
disable-model-invocation: true
---

You have been provided a spec file (`docs/specs/<slug>/spec.md`). Its
tickets live in `.scratch/<slug>/issues/` as one file per ticket
(`<NN>-<slug>.md`). Each ticket is a self-contained execution
contract: Status, blocking edges, Parallel-with/Conflicts-with fields,
context pointers, an implementation plan, the failing tests to write
first, the repo gates to pass, acceptance criteria, and a Definition
of done. No issue tracker is configured; ticket files are the source
of truth.

The goal is the entire spec implemented on a single **integration
branch**, with every ticket file's Status updated to `done` as work
lands.

The tickets are not a list of steps. They are a **task graph** with blocking relationships between them. This means there is always a **frontier** of tickets which are ready to be grabbed.

Communication to and from subagents should be sparse. Communicate primarily through **context pointers**: to the spec, tickets, research notes, and previous commits. Don't duplicate information already available via pointers.

**Implementer subagents** should be run in the background where possible for maximum concurrency.

## Steps

1. Read the spec and tickets to understand the task graph.

2. (optional) Use an **exploration subagent** to conduct any exploration required by the tickets - relevant codebase files or external documentation. Ensure the exploration subagent can save files - it should save its markdown notes in a directory outside the repo, accessible by all future subagents. This lets **implementer subagents** focus on implementation rather than exploration.

3. Create the integration branch. Open a draft PR after the first merge in step 5 (a branch with no commits ahead of main can't open one), marked as covering the spec and its tickets.

4. Use **implementer subagents** to implement each ticket, each in its own worktree on its own branch. Each implementer subagent:
   - confirms its worktree is based on the integration branch before starting, and resets onto it if not;
   - works the ticket's own Implementation plan and Context pointers - the ticket is the contract, not a hint;
   - writes the ticket's named tests failing-first via `tdd`, then implements;
   - leaves the ticket's Gates section green (`uv run pytest`, ruff, `uvx falsegreen`, file-size cap);
   - reviews the test files it wrote or edited with `test-smell-review` before reporting done;
   - ticks only the acceptance-criteria boxes it verified (never speculatively); DoD items and Status flip happen at merge;
   - merges the integration branch tip into its own branch before reporting done

5. Once an **implementer subagent** completes, merge its work to the integration branch with a **merger subagent**.

6. If this changes the **frontier** of available tickets, kick off more **implementer subagents** to work on the new tickets. This allows for maximum concurrency. Use each ticket's `Parallel with` field to pick simultaneous work; serialize tickets that declare `Conflicts with` on the same files.

7. Once all tickets are complete, call the Skill tool with `code-review` on the integration branch. Fix all issues raised by the code review in a single **implementer subagent**.

8. If a draft PR exists, mark it ready for review. As each ticket merges, tick its remaining Definition-of-done items and flip its Status to `done`. Report the integration branch.

9. Clean up all **implementer subagent** worktrees.
