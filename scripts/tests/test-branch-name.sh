#!/usr/bin/env bash
# Regression tests for scripts/check-branch-name.sh.
# Run: bash scripts/tests/test-branch-name.sh
# Override the binary under test: CHECK_BRANCH_BIN=/tmp/check-branch-name.sh bash scripts/tests/test-branch-name.sh
set -u
root="$(git rev-parse --show-toplevel)"
bin="${CHECK_BRANCH_BIN:-$root/scripts/check-branch-name.sh}"
# shellcheck disable=SC1091
. "$root/scripts/conventions.sh"

pass=0
fail=0
check() { # $1 = want (0 pass, 1 fail), $2 = branch name
  local want="$1" name="$2"
  if "$bin" "$name" >/dev/null 2>&1; then got=0; else got=1; fi
  if [ "$got" = "$want" ]; then
    pass=$((pass + 1))
  else
    fail=$((fail + 1))
    printf 'FAIL (want=%s got=%s): %s\n' "$want" "$got" "$name"
  fi
}

# Valid branch names pass.
check 0 'feat/web-bff'
check 0 'fix/api-login'
check 0 'docs/readme-quickstart'
check 0 'chore/deps-2'
# Exempt refs pass.
check 0 'main'
check 0 'dev'
check 0 'HEAD'
# Every centralized type is accepted with a slug.
for t in $TAIPAN_TYPES; do
  check 0 "$t/some-slug"
done

# Invalid branch names fail.
check 1 'setup-wizard'
check 1 'Feat/web-bff'
check 1 'feat/'
check 1 'feat'
check 1 'feat/Web-Bff'
check 1 'unknown-type/some-slug'
check 1 'feat/some_slug'
check 1 'feat//double-slash'

# Docs lists are generated from the centralized source; fail on drift.
if "$root/scripts/sync-conventions-docs.sh" --check >/dev/null 2>&1; then
  pass=$((pass + 1))
else
  fail=$((fail + 1))
  printf 'FAIL docs drift: run scripts/sync-conventions-docs.sh\n'
fi

printf 'pass=%d fail=%d\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
