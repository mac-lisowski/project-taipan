#!/usr/bin/env bash
# Stop: once per session, if the tree changed but memory did not,
# nudge the agent to update .agents/memory per MEMORY.md.
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
printf '%s\n' "$dirty" | grep -qF '.agents/memory/' && exit 0

touch "$marker"
jq -nc '{decision:"block",reason:"Work tree changed but .agents/memory/ was not updated. Per MEMORY.md: update current.md if work paused or finished; log non-obvious decisions in decisions.md and corrections in learnings.md. Then finish."}'
exit 0
