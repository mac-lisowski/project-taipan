#!/usr/bin/env bash
# SessionStart: inject repo memory and drift warnings into context.
set -u
cat >/dev/null  # consume stdin

root="${DEVIN_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$PWD}}"
cd "$root" 2>/dev/null || exit 0

ctx=""

if [ -f .agents/memory/current.md ]; then
  ctx="Repo memory (.agents/memory/current.md):
$(cat .agents/memory/current.md)"
fi

broken=$(find -L .claude/skills .devin/skills .grok/skills .zcode/skills -type l 2>/dev/null)
[ -n "$broken" ] && ctx="$ctx
WARNING: broken skill symlinks:
$broken"

[ -f AGENTS.md ] || ctx="$ctx
WARNING: AGENTS.md missing."

[ -z "$ctx" ] && exit 0
jq -nc --arg ctx "$ctx" '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$ctx}}'
exit 0
