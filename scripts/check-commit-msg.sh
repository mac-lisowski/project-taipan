#!/usr/bin/env bash
# commit-msg gate: subject non-empty, every line <= 120 chars.
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
exit "$fail"
