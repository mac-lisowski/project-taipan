# Memory hygiene

- 2026-10-05: the user called `current.md` a trash file after a spec
  run; it had grown to 167 lines of appended history.
- Why: `current.md` is read at the start of every session. History
  there is noise and hides the live state.
- How to apply: rewrite `current.md` as a snapshot of now (state,
  next steps, blockers). Never append completed-work narratives.
  Shas and sagas live in git; rationale in `decisions/`; lessons in
  `learnings/`.
