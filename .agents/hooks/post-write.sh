#!/usr/bin/env bash
# PostToolUse check on written files: em dash + ruff for .py files.
# Never blocks; injects findings as additionalContext.
set -u
input=$(cat)
file=$(printf '%s' "$input" | jq -r '.tool_input.file_path // ""' 2>/dev/null) || exit 0
[ -z "$file" ] && exit 0

root="${DEVIN_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$PWD}}"
cd "$root" 2>/dev/null || exit 0
[ -f "$file" ] || exit 0

case "$file" in
  *.agents/skills/*|*.venv/*) exit 0 ;;
esac

notes=""

if grep -Iq $'\xe2\x80\x94' "$file" 2>/dev/null; then
  notes="em dash found in $file - replace it with a hyphen (AGENTS.md rule 1)."
fi

case "$file" in
  *.py)
    out=$(uv run ruff check --output-format concise "$file" 2>/dev/null || true)
    [ -n "$out" ] && notes="$notes ruff issues in $file: $out"
    ;;
esac

[ -z "$notes" ] && exit 0
jq -nc --arg ctx "${notes# }" '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$ctx}}'
exit 0
