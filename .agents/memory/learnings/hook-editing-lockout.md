# Editing live hook files is a loaded gun

A syntax error in `pre-exec.sh` rejects EVERY exec call the harness
makes - the agent loses its hands mid-session. And once `pre-write.sh`
protects the file, the edit/write tools cannot fix it either. The only
recovery is the user patching it manually.

Rules that came out of it (2026-10-04 incident):

- `bash -n` every hook file immediately after writing, before moving on.
- Test hook payloads via files, not command strings: a fixture that
  embeds `git commit`, `sed -i x`, or `core.hooksPath` inside an exec'd
  command triggers the hook on YOUR command, not the fixture's.
- Keep the exec-side gate-file write deterrent out: heuristic, and it
  just demonstrated its blast radius. Tool-level protection in
  `pre-write.sh` plus git-level backstops is the right scope.
