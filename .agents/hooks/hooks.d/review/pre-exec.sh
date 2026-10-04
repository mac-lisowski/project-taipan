#!/usr/bin/env bash
# review mode route: nudge the code-review skill before a commit.
# Route contract: stdin = hook JSON; stdout = plain-text nudge; exit 0.
set -u
input=$(cat)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""' 2>/dev/null) || exit 0

case "$cmd" in
  *"git commit"*)
    printf 'mode=review: before committing, run the code-review skill on the change and the test-smell-review pass on touched tests.'
    ;;
esac
exit 0
