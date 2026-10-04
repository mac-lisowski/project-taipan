#!/usr/bin/env bash
# PostToolUse reminders after shell commands. Never blocks.
set -u
input=$(cat)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""' 2>/dev/null) || exit 0
[ -z "$cmd" ] && exit 0

case "$cmd" in
  *db-revision*)
    jq -nc '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:"Review the generated Alembic migration file before running `uv run db-upgrade`. Autogenerate misses some model changes."}}'
    ;;
esac

exit 0
