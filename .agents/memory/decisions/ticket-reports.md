# Done tickets carry an HTML change report in .scratch/

`<NN>-<slug>.html` sits beside the ticket `.md` under
`.scratch/<slug>/issues/`. Audience: the human skimming what
changed (md tickets are hard to scan). Working state, not durable:
reports stay gitignored like the tickets themselves. Committed
precedent is `docs/specs/implemented/<slug>/spec.html` for style only.

The implement-spec merger writes it at merge time, into the main
checkout (a worktree has no `.scratch/`), from
`git diff <tip-before> <tip-after>` plus the implementer's per-file
intent list. Merge-resolution hunks get their own section.

Enforced two ways: a `Report written` DoD checkbox in the ticket
template, and a `review-stamp.sh` sibling-file check. The check is
scoped: only tickets containing the `Report written` line need the
file, so pre-change done tickets stay exempt. The file must also
contain `<html` (existence-only is too weak). Status grep is now
case/space tolerant in review-stamp.sh and stop-nudge.sh.

to-tickets + implement-spec are vendored from mattpocock/skills:
these edits are local patches, reapply after `npx skills update`
(see learnings/skills-cli.md).
