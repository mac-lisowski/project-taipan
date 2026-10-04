#!/usr/bin/env bash
# PreToolUse guard for file writes. Blocks edits to generated files.
set -u
input=$(cat)
file=$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_input.notebook_path // ""' 2>/dev/null) || exit 0
[ -z "$file" ] && exit 0

block() { printf '%s\n' "$1" >&2; exit 2; }

case "$file" in
  *.venv/*|*.git/*)
    block "Do not write inside .venv or .git."
    ;;
esac

case "$(basename "$file")" in
  uv.lock|skills-lock.json)
    block "$(basename "$file") is generated. Edit pyproject.toml / sources and regenerate instead."
    ;;
esac

root="${DEVIN_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$PWD}}"
ctx=$(printf '%s' "$input" | bash "$root/.agents/hooks/route.sh" pre-write 2>/dev/null || true)
[ -n "$ctx" ] && jq -nc --arg c "$ctx" '{hookSpecificOutput:{hookEventName:"PreToolUse",additionalContext:$c}}'
exit 0
