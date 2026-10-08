#!/usr/bin/env bash
# Regression tests for scripts/check-commit-msg.sh.
# Run: bash scripts/tests/test-commit-msg.sh
# Override the binary under test: CHECK_MSG_BIN=/tmp/check-commit-msg.sh bash scripts/tests/test-commit-msg.sh
set -u
root="$(git rev-parse --show-toplevel)"
bin="${CHECK_MSG_BIN:-$root/scripts/check-commit-msg.sh}"
# shellcheck disable=SC1091
. "$root/scripts/conventions.sh"

pass=0
fail=0
check() { # $1 = want (0 pass, 1 fail), rest = message lines
  local want="$1"; shift
  local tmp; tmp="$(mktemp)"
  printf '%s\n' "$@" > "$tmp"
  if "$bin" "$tmp" >/dev/null 2>&1; then got=0; else got=1; fi
  rm -f "$tmp"
  if [ "$got" = "$want" ]; then
    pass=$((pass + 1))
  else
    fail=$((fail + 1))
    printf 'FAIL (want=%s got=%s): %s\n' "$want" "$got" "$*"
  fi
}

# Valid subjects pass.
check 0 'feat(api): add tenant filter to user list'
check 0 'fix(web): keep focus on login error'
check 0 'docs: rewrite README quickstart'
check 0 'chore(deps): bump ruff to 0.16.10'
check 0 'feat(crypto)!: change default cipher suite'
check 0 'feat!: send an email when a product is shipped'
check 0 'revert(cli): restore deleted flag'
# Exempt subjects skip the format check.
check 0 "Merge branch 'feature-x' into dev"
check 0 'Revert "feat(api): bad change"'
check 0 'fixup! feat(api): wip'
check 0 'squash! feat(api): wip'
# Every centralized type is accepted, with and without a scope.
for t in $TAIPAN_TYPES; do
  check 0 "$t(api): some change"
  check 0 "$t: some change"
done

# Invalid subjects fail.
check 1 'foo: bar'
check 1 'Feat(api): caps type'
check 1 'feat(api) missing colon'
check 1 'feat(api): '
check 1 'feat(API): uppercase scope'
check 1 'feat(bad-scope): unknown scope'
check 1 'feat(api):No space after colon'
check 1 ''
check 1 'just a sentence with no type'

# Length gate still applies to all subjects.
long="$(printf 'feat(api): %120s' 'x')"
check 1 "$long"

printf 'pass=%d fail=%d\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
