# Path normalization: do not string-edit paths before canonicalizing

pre-write.sh once ran `abs=${abs//\.\//\/}` (squeeze `/./` -> `/`)
before `cd dirname && pwd -P`. The replacement also rewrote the `./`
inside `../`: `scripts/../gate` became `scripts/./gate`. dirname
resolved to the wrong directory, the abs path compared unprotected,
and a write landed on the real protected file anyway - a bypass for
every entry in the protection case.

Fix: delete string surgery entirely. `cd "$(dirname ...)" && pwd -P`
already canonicalizes `.` and `..` when the directory exists; appending
the basename covers dirs that do not.

Lesson: canonicalize with the filesystem (`pwd -P`, `realpath`), never
with pattern substitution. Test every protected path with a `..` form,
not just the direct spelling.
