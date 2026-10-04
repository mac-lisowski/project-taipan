#!/usr/bin/env bash
# review-stamp.sh: stamp the current diff as reviewed. Run only after
# a clean code-review pass; the commit gate in pre-exec.sh requires a
# marker bound to the exact staged+unstaged diff. New edits invalidate.
#
# Usage: bash .agents/hooks/review-stamp.sh
set -u
root="${DEVIN_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)}}"
[ -z "$root" ] && root=$PWD
cd "$root" 2>/dev/null || { echo "cannot cd to repo root: $root" >&2; exit 1; }

git rev-parse --git-dir >/dev/null 2>&1 || { echo "not a git repo: $root" >&2; exit 1; }
. "$root/.agents/hooks/mode-lib.sh" 2>/dev/null || { echo "mode-lib.sh missing" >&2; exit 1; }

hash=$(taipan_diff_hash)
[ -z "$hash" ] && { echo "cannot hash diff" >&2; exit 1; }

# Done tickets must have every AC/DoD box ticked before a stamp.
# Whether the ticks are honest is code-review's job (Spec axis).
unchecked=""
for f in .scratch/*/issues/*.md; do
  [ -f "$f" ] || continue
  grep -q '^\*\*Status:\*\* done' "$f" || continue
  grep -qE '^[[:space:]]*- \[ \]' "$f" && unchecked="$unchecked $f"
done
[ -n "$unchecked" ] && {
  echo "stamp refused: done ticket(s) with unchecked boxes:$unchecked" >&2
  echo "verify the AC/DoD items, or flip Status back before stamping." >&2
  exit 1
}

marker="/tmp/taipan-review-$(taipan_key)-$hash"
: >"$marker" || { echo "cannot write $marker" >&2; exit 1; }
printf 'review stamped: %s\n' "$hash"
