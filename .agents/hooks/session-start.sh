#!/usr/bin/env bash
# SessionStart: inject repo memory and drift warnings into context.
set -u
cat >/dev/null  # consume stdin

root="${DEVIN_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)}}"
[ -z "$root" ] && root=$PWD
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

mode=""
if [ -f "$root/.agents/hooks/mode-lib.sh" ]; then
  . "$root/.agents/hooks/mode-lib.sh"
  mode=$(taipan_mode_get)
fi
ctx="$ctx
Activity mode: ${mode:-none}. Set when the phase changes: bash .agents/hooks/agent-mode.sh set <plan|implement|test|review|debug|docs|commit> (AGENTS.md rule 10)."

[ -f AGENTS.md ] || ctx="$ctx
WARNING: AGENTS.md missing."

[ -z "$ctx" ] && exit 0
jq -nc --arg ctx "$ctx" '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$ctx}}'
exit 0
