#!/usr/bin/env bash
# Stop: once per session, if the tree changed but memory did not,
# nudge the agent to update .agents/memory per MEMORY.md. Also nudges
# on done tickets with unchecked AC/DoD boxes.
set -u
input=$(cat)
sid=$(printf '%s' "$input" | jq -r '.session_id // "x"' 2>/dev/null)
marker="/tmp/taipan-mem-nudge-${sid:-x}"
[ -f "$marker" ] && exit 0

root="${DEVIN_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)}}"
[ -z "$root" ] && root=$PWD
cd "$root" 2>/dev/null || exit 0

dirty=$(git status --porcelain 2>/dev/null) || exit 0
[ -z "$dirty" ] && exit 0

reasons=""
printf '%s\n' "$dirty" | grep -qF '.agents/memory/' || \
  reasons="Work tree changed but .agents/memory/ was not updated. Per MEMORY.md: update current.md if work paused or finished; log non-obvious decisions in decisions.md and corrections in learnings.md."

unchecked=""
for f in .scratch/*/issues/*.md; do
  [ -f "$f" ] || continue
  grep -q '^\*\*Status:\*\* done' "$f" || continue
  grep -qE '^[[:space:]]*- \[ \]' "$f" && unchecked="$unchecked $f"
done
[ -n "$unchecked" ] && reasons="$reasons Done ticket(s) with unchecked AC/DoD boxes:$unchecked - verify each item or flip Status back."

[ -z "$reasons" ] && exit 0
touch "$marker"
jq -nc --arg r "$reasons" '{decision:"block",reason:$r}'
exit 0
