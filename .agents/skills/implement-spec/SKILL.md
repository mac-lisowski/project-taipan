---
name: implement-spec
description: "Implement the result of /to-spec and /to-tickets in code."
disable-model-invocation: true
---

You have been provided a spec file (`docs/specs/planned/<slug>/spec.md`). Its
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
   - ends its report-back with a per-file intent list: path, what changed, why, 1-2 sentences each (the merger builds the HTML report from it);
   - ticks only the acceptance-criteria boxes it verified (never speculatively); DoD items and Status flip happen at merge;
   - merges the integration branch tip into its own branch before reporting done

5. Once an **implementer subagent** completes, merge its work to the integration branch with a **merger subagent**. The merger also writes the ticket's report at `.scratch/<slug>/issues/<NN>-<slug>.html` in the **main checkout** (a worktree has no `.scratch/`; pass the absolute path) per the report template below. `.scratch/` is gitignored so file-writing tools refuse it - the merger writes the file via a shell heredoc. The ticket's contribution is `git diff <integration-tip-before> <integration-tip-after>`; if the merge resolved conflicts, the report gets a "merge resolution" section naming the hunks the merger rewrote - the implementer's intent list does not cover them.

6. If this changes the **frontier** of available tickets, kick off more **implementer subagents** to work on the new tickets. This allows for maximum concurrency. Use each ticket's `Parallel with` field to pick simultaneous work; serialize tickets that declare `Conflicts with` on the same files.

7. Once all tickets are complete, call the Skill tool with `code-review` on the integration branch. Fix all issues raised by the code review in a single **implementer subagent**.

8. If a draft PR exists, mark it ready for review. As each ticket merges: confirm its report file exists, then tick its remaining Definition-of-done items, then flip its Status to `done`. Order matters - `review-stamp.sh` refuses to stamp a done ticket with unchecked boxes or a missing report. Once the PR carries the status line `implemented (PR #N)`, `git mv docs/specs/planned/<slug> docs/specs/implemented/` so the directory shows what is left. Report the integration branch.

9. Clean up all **implementer subagent** worktrees.

## Ticket report template

Every merged ticket ships a report at
`.scratch/<slug>/issues/<NN>-<slug>.html`. Rules:

- Self-contained HTML. Tailwind and Mermaid via CDN, no build step.
- STE100 prose, plain ASCII, no em dashes. Under ~100 lines.
- Header: ticket number + title, branch, merge commit, spec path.
- One section per changed file: path, added/modified/deleted tag,
  1-2 sentences on what changed and why.
- Mermaid only when the change has a flow or shape worth drawing.
- Footer lists the gates that ran and their result.

<report-template>

<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Ticket NN report - title</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>mermaid.initialize({startOnLoad:true, theme:'neutral'});</script>
<style>
  body { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
  .lbl { font-size: 10px; letter-spacing: .05em;
         text-transform: uppercase; color: #6b7280; }
</style>
</head>
<body class="bg-slate-50 text-slate-800 text-sm">
<div class="max-w-4xl mx-auto px-6 py-10">

  <header class="mb-8">
    <h1 class="text-2xl font-bold mb-2">NN: ticket title</h1>
    <p class="text-slate-500">Branch <code>branch</code>, commit
      <code>sha</code>. Spec <code>docs/specs/implemented/slug/spec.md</code>,
      ticket <code>NN-slug.md</code>.</p>
  </header>

  <section class="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
    <h2 class="font-bold mb-4">What changed</h2>
    <p>One or two sentences: the behaviour this ticket adds, from
    the user's perspective.</p>
  </section>

  <!-- one section per changed file -->
  <section class="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
    <p class="lbl mb-1">modified</p>
    <h2 class="font-bold mb-2"><code>path/to/file.py</code></h2>
    <p>1-2 sentences: what changed in this file and why.</p>
  </section>

  <!-- optional: only when a flow or shape is worth drawing -->
  <section class="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
    <h2 class="font-bold mb-4">How it fits</h2>
    <div class="mermaid">
graph LR
  A[input] --> B[new module] --> C[output]
    </div>
  </section>

  <footer class="bg-slate-800 text-slate-100 rounded-xl p-6">
    <h2 class="font-bold mb-2">Gates</h2>
    <ul class="list-disc ml-5 space-y-1 text-slate-300">
      <li>pytest files: pass</li>
      <li>ruff check + format: pass</li>
      <li>falsegreen + test-smell-review: clean</li>
      <li>code-review + review-stamp: clean</li>
    </ul>
  </footer>
</div>
</body>
</html>

</report-template>
