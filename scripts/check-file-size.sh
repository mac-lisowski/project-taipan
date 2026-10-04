#!/usr/bin/env bash
# Hard cap on source file length (lines). Enforced by pre-commit
# and the CI lint job. Exclusions are deliberate: vendored skills,
# generated files, lockfiles. Add a path here only with a comment
# saying why.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

MAX_LOC=300
fail=0

while IFS= read -r file; do
  lines=$(wc -l < "$file")
  if [ "$lines" -gt "$MAX_LOC" ]; then
    printf '%4d > %d  %s\n' "$lines" "$MAX_LOC" "$file"
    fail=1
  fi
done < <(
  git ls-files \
    | grep -E '\.(py|ts|tsx|js|jsx|mjs|cjs|sh)$' \
    | grep -vE '^\.agents/skills/' \
    | grep -vE '(^|/)alembic/versions/' \
    | grep -vE '(^|/)next-env\.d\.ts$' \
    | grep -vE '\.(min|lock)\.' \
    | grep -vE '(^|/)(uv\.lock|pnpm-lock\.yaml|skills-lock\.json)$' \
    | grep -vE '(node_modules|\.next|dist|\.venv)/'
)

if [ "$fail" -ne 0 ]; then
  echo "file-size: files over $MAX_LOC lines. Split the file, or exempt"
  echo "the path in scripts/check-file-size.sh with a reason."
  exit 1
fi
