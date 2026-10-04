#!/usr/bin/env bash
# test mode route: before a commit, remind that green still needs the
# J1-J6 judgment pass.
# Route contract: stdin = hook JSON; stdout = plain-text nudge; exit 0.
set -u
input=$(cat)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""' 2>/dev/null) || exit 0

case "$cmd" in
  *"git commit"*)
    printf 'mode=test: tests you wrote must still pass the test-smell-review judgment pass (J1-J6) before commit (AGENTS.md rule 9).'
    ;;
esac
exit 0
