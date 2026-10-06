#!/usr/bin/env bash
# PreToolUse guard for shell commands. Reads hook JSON on stdin.
# Exit 2 = block (stderr is the reason). Anything else = allow.
set -u
input=$(cat)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""' 2>/dev/null) || exit 0
[ -z "$cmd" ] && exit 0
# Heredoc bodies fed to cat/tee write-sinks are data, not commands:
# prose inside a cat > f <<EOF payload (docs saying "git commit",
# sample SQL with DROP TABLE) must not trip the gates. A body is
# stripped only when every << opener on the line sits on a cat/tee
# command and the line carries no pipe, substitution, backtick,
# eval, or process substitution - executing sinks (bash <<EOF,
# x|sh, eval "$(...)", tee >(sh)) run their bodies, so they keep
# the flat match. << inside quotes, comments, or ${...} spans is
# not an opener; delimiters must be plain word chars. An
# unterminated body strips to end of input, matching what the
# shell would read.
cmd=$(printf '%s\n' "$cmd" | awk '
BEGIN {
  SQ = sprintf("%c", 39); DQ = sprintf("%c", 34)
  BS = sprintf("%c", 92); TB = sprintf("%c", 9)
  STOP = " " TB ";&|()<>$`"
}
{
  if (ntags) {
    # Only <<- tolerates an indented terminator; a wrong hit just
    # ends stripping early, which re-checks more text. Safe side.
    l = $0
    if (dsh[1]) sub(/^[ \t]+/, "", l)
    if (l == tag[1]) {
      for (k = 1; k < ntags; k++) { tag[k] = tag[k + 1]; dsh[k] = dsh[k + 1] }
      ntags--
    }
    next
  }
  print
  line = $0
  if (line ~ /[|`]/ || index(line, "$(") > 0 || line ~ /[<>][(]/) next
  if (line ~ /(^|[^A-Za-z_])eval([^A-Za-z_]|$)/) next
  # Every segment holding a bare << must be a cat/tee sink; one
  # executing sink anywhere on the line means no stripping at all.
  norm = line
  gsub(/&&|\|\|/, ";", norm)
  ns = split(norm, seg, /[;()]+/)
  safe = 0
  for (s = 1; s <= ns; s++) {
    if (seg[s] ~ /<<[^<]|<<$/) {
      if (seg[s] ~ /^[ \t]*(sudo[ \t]+)?(cat|tee)[ \t><]/) safe = 1
      else { safe = 0; break }
    }
  }
  if (!safe) next
  # Find <<TAG openers outside quotes on the sink line. The delimiter
  # is the full word with quote chars removed, mid-word quotes and
  # escaped chars included.
  n = length(line); qstate = 0
  for (i = 1; i <= n; i++) {
    c = substr(line, i, 1)
    if (qstate == 1) { if (c == SQ) qstate = 0; continue }
    if (qstate == 2) { if (c == BS) { i++; continue } if (c == DQ) qstate = 0; continue }
    if (c == BS) { i++; continue }
    if (c == SQ) { qstate = 1; continue }
    if (c == DQ) { qstate = 2; continue }
    if (c == "#") break
    if (c == "$" && substr(line, i + 1, 1) == "{") {
      # A << inside ${...} is not an opener; a phantom tag pulled
      # from it can never terminate and would hide unchecked lines.
      depth = 1
      while (depth > 0 && ++i <= n) {
        e = substr(line, i, 1)
        if (e == "{") depth++
        else if (e == "}") depth--
        else if (e == SQ) { while (++i <= n && substr(line, i, 1) != SQ); }
        else if (e == DQ) { while (++i <= n && substr(line, i, 1) != DQ); }
      }
      continue
    }
    if (c == "<" && substr(line, i + 1, 1) == "<" && substr(line, i + 2, 1) != "<" && substr(line, i - 1, 1) != "<") {
      j = i + 2
      dashed = 0
      if (substr(line, j, 1) == "-") { j++; dashed = 1 }
      while (j <= n && index(" " TB, substr(line, j, 1))) j++
      delim = ""
      while (j <= n) {
        ch = substr(line, j, 1)
        if (index(STOP, ch) == 0) {
          if (ch == SQ || ch == DQ) {
            j++
            while (j <= n && substr(line, j, 1) != ch) { delim = delim substr(line, j, 1); j++ }
            if (j <= n) j++
            continue
          }
          if (ch == BS) { j++; if (j <= n) { delim = delim substr(line, j, 1); j++ } continue }
          delim = delim ch; j++
          continue
        }
        break
      }
      if (delim ~ /^[-._A-Za-z0-9]+$/) { tag[++ntags] = delim; dsh[ntags] = dashed }
      i = j - 1
    }
  }
}') || cmd=""
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

# Branch names must be <type>/<slug>; pre-commit, pre-push, and CI re-check.
new_branch=""
case "$cmd_flat" in
  *"git checkout -b "*|*"git checkout -B "*)
    new_branch=$(printf '%s' "$cmd_flat" | sed -n 's/.*checkout -[bB] \([^ ;&|]*\).*/\1/p' | tr -d "'\"")
    ;;
  *"git switch -c "*|*"git switch -C "*)
    new_branch=$(printf '%s' "$cmd_flat" | sed -n 's/.*switch -[cC] \([^ ;&|]*\).*/\1/p' | tr -d "'\"")
    ;;
  *"git branch "*)
    new_branch=$(printf '%s' "$cmd_flat" | sed -n 's/.*git branch \([^ ;&|]*\).*/\1/p' | tr -d "'\"")
    case "$new_branch" in -*|"") new_branch="" ;; esac
    ;;
esac
case "$new_branch" in -*|"") new_branch="" ;; esac
if [ -n "$new_branch" ]; then
  if ! out=$("$root/scripts/check-branch-name.sh" "$new_branch" 2>&1); then
    block "$out"
  fi
fi
ctx=$(printf '%s' "$input" | bash "$root/.agents/hooks/route.sh" pre-exec 2>/dev/null || true)
[ -n "$ctx" ] && jq -nc --arg c "$ctx" '{hookSpecificOutput:{hookEventName:"PreToolUse",additionalContext:$c}}'
exit 0
