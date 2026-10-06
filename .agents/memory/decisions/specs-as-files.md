# Specs in docs/specs/, tickets in .scratch/, no issue tracker

to-spec writes `docs/specs/planned/<slug>/spec.md`; implement-spec moves
the whole slug dir to `docs/specs/implemented/` once its PR carries the
status line `implemented (PR #N)`. The directory split answers "what is
left" with `ls` alone; the Status line inside spec.md stays as the
merge record. to-tickets writes one file per ticket in
`.scratch/<slug>/issues/` (gitignored, upstream path). The Matt
Pocock pack assumes an issue tracker with triage labels - files
replace it. code-review resolves specs from both subdirs by branch
name.
