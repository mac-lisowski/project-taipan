# Hook root resolution

Parent hooks must resolve the repo root the same way `route.sh` and
`mode-lib.sh` do: `$DEVIN_PROJECT_DIR`, then `$CLAUDE_PROJECT_DIR`,
then the script's own location (`dirname $0/../..`), then `pwd`.

Using `$PWD` as the third tier breaks mode routing when the harness
runs a hook from a subdirectory with no env vars set: the route path
`<subdir>/.agents/hooks/route.sh` does not exist, so routing fails
open and silently never fires.

A code review of the mode-hook diff caught this in all five parent
scripts; fixed 2026-10-04. Keep new hook scripts on the same chain.
