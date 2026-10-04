#!/usr/bin/env bash
# Mode router. Parent hooks call: printf '%s' "$input" | route.sh <event>
# Dispatches to hooks.d/<mode>/<event>.sh when a mode is active.
# Route contract: stdin = hook JSON; env TAIPAN_MODE, TAIPAN_TARGET,
# TAIPAN_ROOT; stdout = plain-text nudge; always exit 0, never block.
# A route's nudge fires once per mode-set (dedup marker); changing or
# clearing the mode resets markers via agent-mode.sh.
set -u
input=$(cat)
event="${1:-}"
# Event names are fixed lowercase tokens; anything else would only
# smuggle path segments into hooks.d/.
case "$event" in
  ""|*[!a-z-]*) exit 0 ;;
esac

# Skip inside subagents: hooks fire there too (input carries agent_id),
# but mode routing is top-level and recursion is a documented failure mode.
agent_id=$(printf '%s' "$input" | jq -r '.agent_id // ""' 2>/dev/null) || agent_id=""
[ -n "$agent_id" ] && exit 0

root="${DEVIN_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)}}"
[ -z "$root" ] && root=$PWD
. "$root/.agents/hooks/mode-lib.sh" 2>/dev/null || exit 0

mode=$(taipan_mode_get)
# The mode file lives in world-writable /tmp. Unvalidated content is a
# path-traversal primitive: $mode lands inside the route path below.
taipan_mode_valid "$mode" || exit 0

route="$root/.agents/hooks/hooks.d/$mode/$event.sh"
[ -f "$route" ] || exit 0

target=$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_input.notebook_path // .tool_input.command // ""' 2>/dev/null) || target=""
out=$(TAIPAN_MODE="$mode" TAIPAN_TARGET="$target" TAIPAN_ROOT="$root" \
  timeout 8 bash "$route" <<<"$input" 2>/dev/null) || true
[ -z "$out" ] && exit 0

# Once per mode-set. Noclobber create claims the marker atomically, so
# two concurrent calls cannot both fire.
marker="/tmp/taipan-route-$(taipan_key)-${mode}-${event}"
( set -C; : >"$marker" ) 2>/dev/null || exit 0
printf '%s' "$out"
exit 0
