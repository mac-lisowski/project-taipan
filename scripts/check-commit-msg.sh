#!/usr/bin/env bash
# commit-msg gate: Conventional Commits subject, plus 120-char lines.
# Format: <type>(optional scope)(optional !): <description>
# Scopes: docs/commit-convention.md. App and package scopes are read
# from apps/* and packages/*; generic scopes are listed below.
# Skips #-comment lines and everything under the `commit -v` scissors;
# git strips those after this hook runs.
set -u
msg_file="${1:?usage: check-commit-msg.sh <message-file>}"
[ -f "$msg_file" ] || { echo "no message file: $msg_file" >&2; exit 1; }

fail=0
subject=$(awk '{ sub(/\r$/,""); if ($0 ~ /[^[:space:]]/ && $0 !~ /^#/) { print; exit } }' "$msg_file")
if [ -z "$subject" ]; then
  echo "commit message has an empty subject line." >&2
  fail=1
fi
if [ "${#subject}" -gt 120 ]; then
  echo "commit subject is ${#subject} chars; max 120." >&2
  fail=1
fi
if awk '
  /^# ------------------------ >8 -/ { exit bad+0 }
  { sub(/\r$/, "") }
  /^#/ { next }
  length($0) > 120 { printf "%s:%d: %d chars\n", FILENAME, NR, length($0) > "/dev/stderr"; bad=1 }
  END { exit bad+0 }
' "$msg_file"; then
  :
else
  echo "keep every commit-message line <= 120 chars." >&2
  fail=1
fi

# Exempt subjects skip the format check; the length gate still applies.
case "$subject" in
  Merge\ *|Revert\ *|fixup!\ *|squash!\ *|amend!\ *) exit "$fail" ;;
esac

TYPES='feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert'
GENERIC='repo|ci|docs|deps|scripts|evals|docker|devcontainer|agents|hooks|github'
allowed="$GENERIC"
if top="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  for d in "$top"/apps/*/ "$top"/packages/*/; do
    [ -d "$d" ] || continue
    allowed="$allowed|$(basename "$d")"
  done
fi

if ! printf '%s' "$subject" | grep -Eq "^($TYPES)(\([a-z0-9-]+\))?(!)?: .+"; then
  echo "subject must be '<type>(scope)!: description', e.g. 'feat(api): add login'." >&2
  echo "types: feat fix docs style refactor perf test build ci chore revert." >&2
  echo "scopes: docs/commit-convention.md." >&2
  fail=1
else
  scope="$(printf '%s' "$subject" | sed -n 's/^[^(]*(\([a-z0-9-]*\)).*/\1/p')"
  if [ -n "$scope" ] && ! printf '%s' "$scope" | grep -Eq "^($allowed)$"; then
    echo "unknown scope '$scope'. See docs/commit-convention.md for the list." >&2
    fail=1
  fi
fi
exit "$fail"
