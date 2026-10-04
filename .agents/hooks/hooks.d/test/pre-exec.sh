#!/usr/bin/env bash
# test mode route: before a commit, remind that green still needs the
# J1-J6 judgment pass.
# Route contract: env TAIPAN_TARGET carries the command; stdin has the hook
# JSON if needed; stdout = plain-text nudge; exit 0.
set -u
cmd="${TAIPAN_TARGET:-}"

case "$cmd" in
  *"git commit"*)
    printf 'mode=test: tests you wrote must still pass the test-smell-review judgment pass (J1-J6) before commit (AGENTS.md rule 9).'
    ;;
esac
exit 0
