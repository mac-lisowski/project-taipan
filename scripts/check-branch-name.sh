#!/usr/bin/env bash
# Branch-name gate: <type>/<slug>, e.g. feat/web-bff.
# Usage: check-branch-name.sh [branch] (default: current branch).
# Exempts main, dev, master, and detached HEAD.
# Types come from scripts/conventions.sh; see docs/commit-convention.md.
set -u
# shellcheck disable=SC1091
. "$(cd "$(dirname "$0")" && pwd)/conventions.sh"

name="${1:-$(git rev-parse --abbrev-ref HEAD 2>/dev/null || printf 'HEAD')}"
case "$name" in
  main|dev|master|HEAD) exit 0 ;;
esac
TYPES="$(printf '%s' "$TAIPAN_TYPES" | tr ' ' '|')"
if printf '%s' "$name" | grep -Eq "^($TYPES)/[a-z0-9-]+$"; then
  exit 0
fi
echo "branch '$name' must be '<type>/<slug>', e.g. 'feat/web-bff'." >&2
echo "types: $TAIPAN_TYPES. See docs/commit-convention.md." >&2
exit 1
