#!/usr/bin/env bash
# Unreached-export check for apps/web/src/components. Every module
# in there must be reached: imported by some file outside the
# components dir, or by a component that is. src/ui is exempt by
# design - the design-system barrel is library surface, unused
# exports there are stock, not dead weight. Enforced by pre-commit
# and CI.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

dir=apps/web/src/components
fail=0
report() { echo "unreached-components: no importer: $1"; fail=1; }

mods=()
while IFS= read -r file; do
  # Word-boundary via char classes: [[:<:]] is not portable across grep builds.
  grep -qE '(^|[^A-Za-z0-9_])export([^A-Za-z0-9_]|$)' "$file" || continue
  mods+=("$file")
done < <(find "$dir" -type f \( -name '*.ts' -o -name '*.tsx' \) | sort)

in_live() {
  for got in $live; do [ "$got" = "$1" ] && return 0; done
  return 1
}

# The import specifier, not the symbol: static imports, next/dynamic,
# React.lazy and bare import() all embed the same module path string.
# Matching by stem assumes unique stems under src/components.
spec_re() {
  local stem=${1##*/}
  printf "['\"](@/components/|\\.\\.?/)([A-Za-z0-9_-]+/)*%s['\"]" "${stem%.*}"
}

live=""
# Seeds: importers outside src/components (pages, libs, tests).
for file in ${mods[@]+"${mods[@]}"}; do
  if git grep -qE "$(spec_re "$file")" -- 'apps/web' ":!$dir" 2>/dev/null; then
    live="$live $file"
  fi
done

# Fixpoint: a component only reached by reached components is reached.
changed=1
while [ "$changed" -eq 1 ]; do
  changed=0
  for file in ${mods[@]+"${mods[@]}"}; do
    in_live "$file" && continue
    for parent in $live; do
      if git grep -qE "$(spec_re "$file")" -- "$parent" 2>/dev/null; then
        live="$live $file"
        changed=1
        break
      fi
    done
  done
done

for file in ${mods[@]+"${mods[@]}"}; do
  in_live "$file" && continue
  report "$file"
done

if [ "$fail" -ne 0 ]; then
  echo "unreached-components: modules above have zero importers."
  echo "Delete them, or wire them into a route."
fi
exit "$fail"
