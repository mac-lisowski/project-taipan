#!/usr/bin/env bash
# Stop: once per session, if the tree changed but memory did not,
# nudge the agent to update .agents/memory per MEMORY.md. Also nudges
# on done tickets with unchecked AC/DoD boxes or a missing report.
set -u
input=$(cat)
sid=$(printf '%s' "$input" | jq -r '.session_id // "x"' 2>/dev/null)

root="${DEVIN_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)}}"
[ -z "$root" ] && root=$PWD
cd "$root" 2>/dev/null || exit 0
. "$root/.agents/hooks/mode-lib.sh" 2>/dev/null || true

dirty=$(git status --porcelain 2>/dev/null) || exit 0
[ -z "$dirty" ] && exit 0

reasons=""
printf '%s\n' "$dirty" | grep -qF '.agents/memory/' || \
  reasons="Work tree changed but .agents/memory/ was not updated. Per MEMORY.md: update current.md if work paused or finished; log non-obvious decisions in decisions.md and corrections in learnings.md."

# Advisory copy of the stamp gate: same scan, so the two stay in step.
if type taipan_done_ticket_gaps >/dev/null 2>&1; then
  unchecked=""
  missing=""
  while IFS=' ' read -r kind path; do
    case "$kind" in
      unchecked) unchecked="$unchecked $path" ;;
      report) missing="$missing $path" ;;
    esac
  done < <(taipan_done_ticket_gaps)
  [ -n "$unchecked" ] && reasons="$reasons Done ticket(s) with unchecked AC/DoD boxes:$unchecked - verify each item or flip Status back."
  [ -n "$missing" ] && reasons="$reasons Done ticket(s) with no HTML report:$missing - the implement-spec merger writes it next to the ticket file."
fi

[ -z "$reasons" ] && exit 0
# Once per session per reason set: a new gap type re-nudges.
if type taipan_hash >/dev/null 2>&1; then
  sfx=$(printf '%s' "$reasons" | taipan_hash)
else
  sfx=once
fi
marker="/tmp/taipan-mem-nudge-${sid:-x}-$sfx"
[ -f "$marker" ] && exit 0
touch "$marker"
jq -nc --arg r "$reasons" '{decision:"block",reason:$r}'
exit 0
