#!/usr/bin/env bash
# Dockerfile gate: every Dockerfile whose build context is the repo
# root is scanned. Every COPY/ADD context source must resolve as a root-relative
# path. --from= copies (build stages) and ${VAR} sources are skipped;
# .dockerignore can still exclude an existing file, so the CI docker
# build remains the authority. RUN lines using `pnpm -C/--dir` are
# flagged: corepack resolves packageManager from cwd, not -C's dir.
# Completeness: an app Dockerfile running uv sync must COPY every
# [tool.uv.sources] workspace member of that app as a directory.
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

# Completeness: an app Dockerfile running uv sync must copy every
# [tool.uv.sources] member of that app as a DIRECTORY. A manifest-only
# copy passes uv's resolution but the install fails in CI with
# "Distribution not found at: file:///app/packages/<name>". Non-app
# Dockerfiles sync the root workspace, so they need every package;
# whole-tree copies (COPY packages) do not count as per-dep copies.
normalize() { # $1=Dockerfile: join continuations, drop comment lines
  sed -e ':a' -e '/\\$/N; s/\\\n/ /; ta' "$1" | grep -vE '^[[:space:]]*#'
}

# Context-source tokens of COPY/ADD lines: instruction and flags stripped,
# --from stage copies excluded, dest token dropped. Consumes stdin.
copy_sources() {
  awk '
    toupper($0) ~ /^[[:space:]]*(COPY|ADD)[[:space:]]/ {
      if ($0 ~ /--[[:space:]]*from=/) next
      line = $0
      sub(/^[[:space:]]*[A-Za-z]+[[:space:]]+/, "", line)
      while (line ~ /^[[:space:]]*--/) { sub(/^[[:space:]]*--[^[:space:]]+[[:space:]]*/, "", line) }
      n = split(line, tok, /[[:space:]]+/)
      if (n < 2) next
      if (tok[1] ~ /^\[/) { for (i = 1; i < n; i++) { gsub(/[][]|"|,/, "", tok[i]); if (tok[i] != "") print tok[i] } }
      else { for (i = 1; i < n; i++) print tok[i] }
    }
  '
}

workspace_deps() { # $1=pyproject.toml -> [tool.uv.sources] members, one per line
  awk '
    /^[[:space:]]*\[/ { in_src = ($0 ~ /^\[[[:space:]]*tool\.uv\.sources[[:space:]]*\]/); next }
    in_src && /(^|[[:space:]])workspace[[:space:]]*=[[:space:]]*true/ {
      name = $0; sub(/[[:space:]]*=.*/, "", name); gsub(/^[[:space:]]+|[[:space:]]+$/, "", name)
      if (name != "") print name
    }
  ' "$1"
}

for df in apps/*/Dockerfile*; do
  [ -f "$df" ] || continue
  app=${df#apps/}; app=${app%%/*}
  [ -f "apps/$app/pyproject.toml" ] || continue
  norm=$(normalize "$df")
  printf '%s' "$norm" | grep -qiE '^[[:space:]]*run[[:space:]].*uv sync' || continue
  srcs=$(printf '%s' "$norm" | copy_sources)
  for dep in $(workspace_deps "apps/$app/pyproject.toml"); do
    printf '%s' "$srcs" \
      | grep -qiE "(^|[[:space:]])packages/$dep([[:space:]]|$)" \
      || report "$df missing COPY of workspace package directory 'packages/$dep' (apps/$app dependency)"
  done
done

for df in docker/*/Dockerfile* .devcontainer/Dockerfile*; do
  [ -f "$df" ] || continue
  norm=$(normalize "$df")
  printf '%s' "$norm" | grep -qiE '^[[:space:]]*run[[:space:]].*uv sync' || continue
  for manifest in packages/*/pyproject.toml; do
    pkg=${manifest%/pyproject.toml}
    printf '%s' "$norm" | grep -qiE "^[[:space:]]*(copy|add)[[:space:]]+.*${pkg}(/| )" \
      || report "$df missing COPY source for workspace package '$pkg'"
  done
done

exit "$fail"
