#!/usr/bin/env bash
# Regenerate the type/scope lists in docs/commit-convention.md from conventions.sh.
# Usage: sync-conventions-docs.sh [--check]; --check fails on drift instead of writing.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
. "$here/conventions.sh"
doc="$here/../docs/commit-convention.md"
mode="${1:-}"

list_block() { # $1 = space-separated tokens; backticked paragraph ending with a period
  local s="" tok
  for tok in $1; do s="$s\`$tok\`, "; done
  printf '%s\n' "${s%, }." | fold -s -w 64 | sed 's/ *$//'
}

top="$(git rev-parse --show-toplevel)"
areas=""
for d in "$top"/apps/*/ "$top"/packages/*/; do
  [ -d "$d" ] || continue
  areas="$areas $(basename "$d")"
done
areas="$(printf '%s' "$areas" | tr ' ' '\n' | grep -v '^$' | sort -u | tr '\n' ' ')"

export TYPES_BLOCK AREAS_BLOCK GENERIC_BLOCK
TYPES_BLOCK="$(list_block "$TAIPAN_TYPES")"
AREAS_BLOCK="$(list_block "$areas")"
GENERIC_BLOCK="$(list_block "$TAIPAN_GENERIC_SCOPES")"

rendered="$(python3 - "$doc" <<'EOF'
import os, sys
text = open(sys.argv[1]).read()
blocks = {
    "types": os.environ["TYPES_BLOCK"],
    "areas": os.environ["AREAS_BLOCK"],
    "generic": os.environ["GENERIC_BLOCK"],
}
for name, body in blocks.items():
    start = "<!-- conventions:%s:start -->" % name
    end = "<!-- conventions:%s:end -->" % name
    pre, found, rest = text.partition(start)
    assert found, name
    _, found, post = rest.partition(end)
    assert found, name
    text = pre + start + "\n" + body.rstrip("\n") + "\n" + end + post
sys.stdout.write(text)
EOF
)"
if [ "$mode" = "--check" ]; then
  if [ "$rendered" = "$(cat "$doc")" ]; then exit 0; fi
  echo "docs/commit-convention.md drifts from conventions.sh; run scripts/sync-conventions-docs.sh." >&2
  exit 1
fi
printf '%s\n' "$rendered" > "$doc"
