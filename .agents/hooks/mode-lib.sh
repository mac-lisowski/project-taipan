#!/usr/bin/env bash
# Shared helpers for the activity-mode system. Source this; do not run it.
# Mode is a one-word, fixed-vocabulary label the agent declares for its
# current phase. Hooks in hooks.d/ read it to select which checks run.
# Advisory only: routes never block. Hard gates stay unconditional in the
# parent hook scripts.

# shellcheck disable=SC2034
TAIPAN_MODES="plan implement test review debug docs commit"

taipan_root() {
  if [ -n "${DEVIN_PROJECT_DIR:-}" ]; then printf '%s' "$DEVIN_PROJECT_DIR"; return; fi
  if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then printf '%s' "$CLAUDE_PROJECT_DIR"; return; fi
  # cwd is unreliable: the agent may exec agent-mode.sh from a subdir.
  # This file always sits at <root>/.agents/hooks/mode-lib.sh.
  (cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../.." 2>/dev/null && pwd) || printf '%s' "$PWD"
}

# Exact-word membership check. A glob char in $1 stays literal here.
taipan_mode_valid() {
  local m
  for m in $TAIPAN_MODES; do
    [ "$m" = "$1" ] && return 0
  done
  return 1
}

# State is per project, not per session: a script invoked via exec has no
# access to session_id. /tmp clears on reboot, which is the reset.
taipan_key() {
  local root
  root=$(taipan_root)
  if command -v sha1sum >/dev/null 2>&1; then
    printf '%s' "$root" | sha1sum | cut -c1-12
  else
    # cksum is POSIX; keeps the key non-empty when sha1sum is missing.
    printf '%s' "$root" | cksum | awk '{printf "%012x", $1}'
  fi
}

taipan_mode_file() {
  printf '/tmp/taipan-mode-%s' "$(taipan_key)"
}

taipan_mode_get() {
  local f
  f=$(taipan_mode_file)
  [ -f "$f" ] && cat "$f" 2>/dev/null
  return 0
}

# Drop every marker this project left in /tmp (route dedup, nudges).
taipan_clear_markers() {
  rm -f /tmp/taipan-route-"$(taipan_key)"-* /tmp/taipan-nudge-"$(taipan_key)"-* 2>/dev/null
  return 0
}
