#!/usr/bin/env bash
# PostToolUse reminders after shell commands. Never blocks.
set -u
input=$(cat)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""' 2>/dev/null) || exit 0
[ -z "$cmd" ] && exit 0

ctx=""
case "$cmd" in
  *db-revision*)
    ctx="Review the generated Alembic migration file before running \`uv run db-upgrade\`. Autogenerate misses some model changes."
    ;;
esac

root="${DEVIN_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)}}"
[ -z "$root" ] && root=$PWD
route_out=$(printf '%s' "$input" | bash "$root/.agents/hooks/route.sh" post-exec 2>/dev/null || true)
[ -n "$route_out" ] && ctx="${ctx:+$ctx }$route_out"

[ -z "$ctx" ] && exit 0
jq -nc --arg ctx "$ctx" '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$ctx}}'
exit 0
