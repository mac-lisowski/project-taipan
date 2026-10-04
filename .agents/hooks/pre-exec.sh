#!/usr/bin/env bash
# PreToolUse guard for shell commands. Reads hook JSON on stdin.
# Exit 2 = block (stderr is the reason). Anything else = allow.
set -u
input=$(cat)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""' 2>/dev/null) || exit 0
[ -z "$cmd" ] && exit 0
# Match against a whitespace-flattened copy so multi-space or
# line-continued spellings still hit the gates. Quoted forms like
# git "commit" evade by design (README lists the gaps).
cmd_flat=$(printf '%s' "$cmd" | tr -s '[:space:]' ' ')

block() { printf '%s\n' "$1" >&2; exit 2; }

first=$(printf '%s' "$cmd_flat" | awk '{print $1}')

# AGENTS.md rule 3: Python commands go through uv run.
case "$first" in
  python|python3|pytest|ruff|alembic|uvicorn)
    block "Use 'uv run $first ...' instead. Never run $first directly (AGENTS.md rule 3)."
    ;;
  pip|pip3)
    block "Use 'uv add <dep>' or 'uv add <dep> --dev' instead of pip."
    ;;
esac

case "$cmd_flat" in
  *".venv/bin/"*|"source .venv"*|" . .venv"*)
    block "Never activate .venv manually. Use 'uv run <cmd>' (AGENTS.md rule 3)."
    ;;
esac

# Dangerous commands.
case "$cmd_flat" in
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
  *"git config"*"ooks"[Pp]"ath"*|*"git -c"*"ooks"[Pp]"ath"*|*"GIT_CONFIG_PARAMETERS"*"="*"ooks"[Pp]"ath"*|*"GIT_CONFIG_KEY"*"="*"ooks"[Pp]"ath"*)
    case "$cmd_flat" in
      *--get*|*--list*) ;;
      *) block "Changing core.hooksPath blocked." ;;
    esac
    ;;
  *commit-tree*|*update-ref*)
    block "Git plumbing that mints commits or moves refs is blocked."
    ;;
esac

root="${DEVIN_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)}}"
[ -z "$root" ] && root=$PWD

# Commit gate (AGENTS.md rule 11): a commit needs a review marker bound
# to the exact staged+unstaged diff. Stamp via review-stamp.sh after a
# clean code-review pass; edits after stamping invalidate it. Bypass
# vectors are denied. Subagent calls are exempt: implement-spec
# subagents are gated by the orchestrator's code-review step instead.
case "$cmd_flat" in
  *"git commit"*|*"git -"*"commit"*)
    # Bypass flags are scoped to the commit invocation's own args so a
    # '-n' in a neighbouring compound command does not false-block.
    case "$cmd_flat" in
      *"git -C "*|*"git --git-dir"*)
        block "Commits via -C/--git-dir bind the marker to this repo's hash. cd there and commit plainly."
        ;;
      *commit*";"*commit*|*commit*"&"*commit*|*commit*"|"*commit*)
        block "One commit per command: each commit needs its own review marker."
        ;;
      *--no-veri*|*"SKIP="*|*"HUSKY="*|*"LEFTHOOK="*|*"OVERCOMMIT_DISABLE"*)
        block "Commit bypass blocked: hooks and the review gate must run."
        ;;
    esac
    cargs=${cmd_flat#*commit}; cargs=${cargs%%[;&|]*}
    set -f
    for a in $cargs; do
      case "$a" in
        -[a-zA-Z]*)
          case "${a#-}" in
            *n*) block "Commit bypass blocked: hooks and the review gate must run." ;;
          esac
          ;;
      esac
    done
    set +f
    agent_id=$(printf '%s' "$input" | jq -r '.agent_id // ""' 2>/dev/null) || agent_id=""
    if [ -z "$agent_id" ]; then
      . "$root/.agents/hooks/mode-lib.sh" 2>/dev/null || block "Review gate cannot verify state (mode-lib.sh missing) - ask the user."
      dhash=$(cd "$root" 2>/dev/null && taipan_diff_hash)
      [ -z "$dhash" ] && block "Review gate cannot compute the diff hash (project root unreachable) - ask the user."
      marker="/tmp/taipan-review-$(taipan_key)-$dhash"
      [ -f "$marker" ] || block "Review gate: run the code-review skill on the uncommitted diff (HEAD..worktree) plus test-smell-review on touched tests, then 'bash .agents/hooks/review-stamp.sh'. The stamp binds to this diff; new edits invalidate it."
    fi
    ;;
esac
ctx=$(printf '%s' "$input" | bash "$root/.agents/hooks/route.sh" pre-exec 2>/dev/null || true)
[ -n "$ctx" ] && jq -nc --arg c "$ctx" '{hookSpecificOutput:{hookEventName:"PreToolUse",additionalContext:$c}}'
exit 0
