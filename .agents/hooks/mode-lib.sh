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

# Hash stdin to a short hex id. sha256sum, then shasum (macOS), then
# POSIX cksum so the value is never empty.
taipan_hash() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum | cut -c1-16
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 | cut -c1-16
  else
    cksum | awk '{printf "%016x", $1}'
  fi
}

# Digest of the change a commit could record, bound to worktree bytes
# rather than index state: every path differing from HEAD contributes
# its status, path, and worktree blob hash; staged content that
# diverges from the worktree contributes its cached diff. `git add`
# moves no worktree bytes, so a stamp survives staging; a content edit
# after stamping invalidates it. Run from the repo root.
taipan_diff_hash() {
  {
    # path<TAB>worktree-blob-hash, path-sorted so `git add` (which only
    # reorders status output) cannot change the digest.
    git status --porcelain=v1 --no-renames -z --untracked-files=all 2>/dev/null |
    while IFS= read -r -d '' rec; do
      p=${rec:3}
      if [ -f "$p" ]; then h=$(git hash-object -- "$p" 2>/dev/null); else h=ABSENT; fi
      printf '%s\t%s\n' "$p" "$h"
    done | LC_ALL=C sort
    # stale index: staged content that differs from the worktree is
    # bound too, or a stamp could bless an unreviewed staged version.
    git status --porcelain=v1 --no-renames -z 2>/dev/null |
    while IFS= read -r -d '' rec; do
      case "$rec" in
        [MADRCTU][MADRCTU]*) git diff --cached --full-index -- "${rec:3}" 2>/dev/null ;;
      esac
    done
  } | taipan_hash
}
