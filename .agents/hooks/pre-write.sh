#!/usr/bin/env bash
# PreToolUse guard for file writes. Blocks edits to generated files.
set -u
input=$(cat)
file=$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_input.notebook_path // ""' 2>/dev/null) || exit 0
[ -z "$file" ] && exit 0

block() { printf '%s\n' "$1" >&2; exit 2; }

root="${DEVIN_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)}}"
[ -z "$root" ] && root=$PWD

case "$file" in
  *.venv/*|*.git/*)
    block "Do not write inside .venv or .git."
    ;;
esac

# Gate machinery is protected: a hook the agent can edit is advisory.
# Anchored to the project root so vendored copies under .agents/skills/
# and nested packages stay editable. hooks.d/ routes stay editable:
# they are nudges, not gates.
abs=$file
case "$abs" in /*) ;; *) abs=$PWD/$abs ;; esac
nd=$(cd "$(dirname "$abs")" 2>/dev/null && pwd -P) && abs="$nd/${abs##*/}"
case "$abs" in
  "$root"/.claude/settings*.json|"$root"/.zcode/config*.json|"$root"/.devin/config*.json)
    block "Tool hook manifests are protected. Ask the user to edit them."
    ;;
  "$root"/.pre-commit-config.yaml|"$root"/scripts/check-*.sh)
    block "Gate files are protected. Ask the user to edit them."
    ;;
  "$root"/.agents/hooks/pre-exec.sh|"$root"/.agents/hooks/pre-write.sh|"$root"/.agents/hooks/post-exec.sh|"$root"/.agents/hooks/post-write.sh|"$root"/.agents/hooks/route.sh|"$root"/.agents/hooks/mode-lib.sh|"$root"/.agents/hooks/agent-mode.sh|"$root"/.agents/hooks/review-stamp.sh|"$root"/.agents/hooks/session-start.sh|"$root"/.agents/hooks/stop-nudge.sh)
    block "Hook gate files are protected. Ask the user to edit them."
    ;;
esac

case "$(basename "$file")" in
  uv.lock|skills-lock.json)
    block "$(basename "$file") is generated. Edit pyproject.toml / sources and regenerate instead."
    ;;
esac

ctx=$(printf '%s' "$input" | bash "$root/.agents/hooks/route.sh" pre-write 2>/dev/null || true)
[ -n "$ctx" ] && jq -nc --arg c "$ctx" '{hookSpecificOutput:{hookEventName:"PreToolUse",additionalContext:$c}}'
exit 0
