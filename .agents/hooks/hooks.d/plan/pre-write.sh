#!/usr/bin/env bash
# plan mode route: warn once per mode-set when the agent edits code.
# Route contract: stdin = hook JSON; stdout = plain-text nudge; exit 0.
set -u
input=$(cat)
file=$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_input.notebook_path // ""' 2>/dev/null) || exit 0

case "$file" in
  *.py|*.ts|*.tsx|*.js|*.jsx|*.sql|*.sh|*.ipynb)
    case "$file" in
      */.agents/*|.agents/*|*/docs/*|docs/*|*/memory/*|memory/*|*/tests/*|tests/*|*/test_*.py|test_*.py|*/conftest.py|conftest.py) exit 0 ;;
    esac
    printf 'mode=plan: editing %s. A plan ends at the plan output; implement after the user approves.' "$file"
    ;;
esac
exit 0
