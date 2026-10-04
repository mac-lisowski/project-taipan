#!/usr/bin/env bash
# PreToolUse guard for shell commands. Reads hook JSON on stdin.
# Exit 2 = block (stderr is the reason). Anything else = allow.
set -u
input=$(cat)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""' 2>/dev/null) || exit 0
[ -z "$cmd" ] && exit 0

block() { printf '%s\n' "$1" >&2; exit 2; }

first=$(printf '%s' "$cmd" | awk '{print $1}')

# AGENTS.md rule 3: Python commands go through uv run.
case "$first" in
  python|python3|pytest|ruff|alembic|uvicorn)
    block "Use 'uv run $first ...' instead. Never run $first directly (AGENTS.md rule 3)."
    ;;
  pip|pip3)
    block "Use 'uv add <dep>' or 'uv add <dep> --dev' instead of pip."
    ;;
esac

case "$cmd" in
  *".venv/bin/"*|"source .venv"*|" . .venv"*)
    block "Never activate .venv manually. Use 'uv run <cmd>' (AGENTS.md rule 3)."
    ;;
esac

# Dangerous commands.
case "$cmd" in
  *"git push --force"*|*"git push -f "*|*"git push -f")
    block "Force push blocked."
    ;;
  *"git reset --hard"*|*"git clean -f"*)
    block "Destructive git command blocked."
    ;;
  *"rm -rf /"*|*"rm -rf ~"*|*"rm -rf \$HOME"*|*"rm -rf \*"*)
    block "Dangerous rm -rf target blocked."
    ;;
  *"DROP TABLE"*|*"drop table"*|*"mkfs"*|*"dd if="*)
    block "Destructive command blocked."
    ;;
esac

root="${DEVIN_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$PWD}}"
ctx=$(printf '%s' "$input" | bash "$root/.agents/hooks/route.sh" pre-exec 2>/dev/null || true)
[ -n "$ctx" ] && jq -nc --arg c "$ctx" '{hookSpecificOutput:{hookEventName:"PreToolUse",additionalContext:$c}}'
exit 0
