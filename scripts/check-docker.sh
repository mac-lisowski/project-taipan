#!/usr/bin/env bash
# Dockerfile gate: every Dockerfile whose build context is the repo
# root is scanned. Every COPY/ADD context source must resolve as a root-relative
# path. --from= copies (build stages) and ${VAR} sources are skipped;
# .dockerignore can still exclude an existing file, so the CI docker
# build remains the authority. RUN lines using `pnpm -C/--dir` are
# flagged: corepack resolves packageManager from cwd, not -C's dir.
# Enforced by pre-commit and the CI lint job.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
shopt -s nocasematch

fail=0
report() { echo "check-docker: $1"; fail=1; }

check_src() { # $1=file $2=lineno $3=source
  [[ $3 == *\$* ]] && return 0          # ${VAR} source: unverifiable
  compgen -G "$3" >/dev/null \
    || report "$1:$2 COPY/ADD source '$3' not found at repo root"
}

for df in apps/*/Dockerfile* docker/*/Dockerfile* .devcontainer/Dockerfile*; do
  [ -f "$df" ] || continue
  lineno=0
  while IFS= read -r raw || [ -n "$raw" ]; do
    lineno=$((lineno + 1))
    # Join backslash continuations into one logical line.
    line=$raw
    while [[ $line =~ \\$ ]] && IFS= read -r raw; do
      lineno=$((lineno + 1))
      line="${line%\\} $raw"
    done
    [[ $line =~ ^[[:space:]]*# ]] && continue   # comment
    if [[ $line =~ ^[[:space:]]*run[[:space:]] ]] \
       && [[ $line =~ pnpm[[:space:]]+(-C|--dir|--prefix) ]]; then
      report "$df:$lineno 'pnpm -C/--dir' in RUN: corepack resolves packageManager from cwd; use WORKDIR/cd"
      continue
    fi
    [[ $line =~ ^[[:space:]]*(copy|add)[[:space:]] ]] || continue
    [[ $line == *--from=* ]] && continue        # stage-internal copy
    rest=${line#* }                             # drop instruction word
    if [[ $rest == \[* ]]; then
      # JSON form: quoted entries, the last is the dest.
      mapfile -t srcs < <(printf '%s' "$rest" | grep -oE '"[^"]*"' | tr -d '"')
      [ ${#srcs[@]} -ge 1 ] && unset 'srcs[$((${#srcs[@]}-1))]'
    else
      set -- $rest
      while [ $# -gt 0 ]; do
        case "$1" in --*) shift ;; *) break ;; esac
      done
      [ $# -lt 2 ] && continue                  # nothing to check
      srcs=("$@"); unset 'srcs[$((${#srcs[@]}-1))]'
    fi
    for src in "${srcs[@]:-}"; do
      [ -n "$src" ] && check_src "$df" "$lineno" "$src"
    done
  done < "$df"
done

exit "$fail"
