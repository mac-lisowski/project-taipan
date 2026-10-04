#!/usr/bin/env bash
# review mode route: nudge the code-review skill before a commit.
# Route contract: env TAIPAN_TARGET carries the command; stdin has the hook
# JSON if needed; stdout = plain-text nudge; exit 0.
set -u
cmd="${TAIPAN_TARGET:-}"

case "$cmd" in
  *"git commit"*)
    printf 'mode=review: before committing, run the code-review skill on the change and the test-smell-review pass on touched tests.'
    ;;
esac
exit 0
