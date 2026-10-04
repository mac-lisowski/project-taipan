# Specs in docs/specs/, tickets in .scratch/, no issue tracker

to-spec writes `docs/specs/<slug>/spec.md`; to-tickets writes one file
per ticket in `.scratch/<slug>/issues/` (gitignored, upstream path);
implement-spec reads those files and marks Status done. The Matt
Pocock pack assumes an issue tracker with triage labels - files
replace it. code-review resolves specs from docs/specs/ by branch
name.
