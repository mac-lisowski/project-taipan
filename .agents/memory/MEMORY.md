# Memory index

Long-term agent memory for this repo. AGENTS.md holds the rules;
this dir holds what the agent learned while working.

## Files

- `current.md`: active work, blockers, next step. Read first.
- `decisions.md`: index of `decisions/`, why things are the way they
  are. One file per decision, linked from the index. Append-only.
- `learnings.md`: index of `learnings/`, durable lessons, gotchas,
  user preferences. One file per entry, linked from the index.

## Rules for the agent

- Read `current.md` before starting a task.
- Update `current.md` when work pauses or finishes.
- Log a decision as a new file in `decisions/` plus an index link
  when a non-obvious choice is made.
- Log a lesson as a new file in `learnings/` plus an index link when
  the user corrects you or something breaks in a surprising way.
- Keep entries short. One fact per line. No prose.
