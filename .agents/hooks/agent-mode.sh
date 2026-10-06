#!/usr/bin/env bash
# Agent-declared activity mode. Called by the agent via exec:
#   bash .agents/hooks/agent-mode.sh set <mode>|get|clear|list
# Mode is advisory: hooks.d/<mode>/<event>.sh routes fire nudges.
set -u
. "$(dirname "$0")/mode-lib.sh" || { echo "mode-lib.sh not found" >&2; exit 1; }

cmd="${1:-get}"
case "$cmd" in
  set)
    mode="${2:-}"
    if ! taipan_mode_valid "$mode"; then
      echo "invalid mode '$mode' (valid: $TAIPAN_MODES)" >&2
      exit 1
    fi
    prev=$(taipan_mode_get)
    [ "$prev" = "$mode" ] && { echo "mode=$mode"; exit 0; }
    taipan_clear_markers
    printf '%s' "$mode" >"$(taipan_mode_file)" || exit 1
    echo "mode=$mode"
    ;;
  get)
    m=$(taipan_mode_get)
    echo "${m:-none}"
    ;;
  clear)
    taipan_clear_markers
    rm -f "$(taipan_mode_file)"
    echo "mode cleared"
    ;;
  list)
    echo "$TAIPAN_MODES"
    ;;
  *)
    echo "usage: agent-mode.sh set <mode>|get|clear|list" >&2
    exit 1
    ;;
esac
exit 0
