# Review stamp binds to the session checkout, not a worktree

`review-stamp.sh` and the pre-exec commit gate each resolve the repo
root on their own (`DEVIN_PROJECT_DIR`, then the script's location).
A stamp run inside a `git worktree` writes a marker keyed to that
worktree's path and diff hash. The commit gate fires from the main
checkout's hook manifest, so it looks for a marker keyed to the main
checkout's root and diff. Result: stamp in a worktree, commit there,
gate blocks with "Review gate".

Fix: commit in the checkout that owns the session. If it sits on
another branch, checkout the target branch, commit, switch back.
Carried worktree modifications ride along untouched; `git commit`
with only your files staged still leaves them uncommitted, and the
pre-commit stash/restore cycle preserves them.
