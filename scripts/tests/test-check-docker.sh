#!/usr/bin/env bash
# Regression tests for scripts/check-docker.sh completeness gate.
# Run: bash scripts/tests/test-check-docker.sh
set -u
root="$(git rev-parse --show-toplevel)"
bin="${CHECK_DOCKER_BIN:-$root/scripts/check-docker.sh}"

pass=0
fail=0

# Builds a repo-root fixture in a temp git worktree, writes the given
# Dockerfile at $3, runs the gate, reports exit status.
check() { # $1 = want (0 pass, 1 fail), $2 = case name, $3 = Dockerfile path
  local want="$1" name="$2" dfpath="$3" tmp out
  tmp="$(mktemp -d)"
  mkdir -p "$tmp/apps/api" "$tmp/packages/core" "$tmp/packages/extra" "$tmp/$(dirname "$dfpath")"
  ( cd "$tmp" && git init -q . )
  printf '[project]\nname = "root"\n' > "$tmp/pyproject.toml"
  : > "$tmp/uv.lock"
  : > "$tmp/README.md"
  printf '[project]\nname = "core"\nversion = "0.1.0"\n' > "$tmp/packages/core/pyproject.toml"
  printf '[project]\nname = "extra"\nversion = "0.1.0"\n' > "$tmp/packages/extra/pyproject.toml"
  cat > "$tmp/apps/api/pyproject.toml" <<'TOML'
[project]
name = "api"
version = "0.1.0"
dependencies = ["core"]

[tool.uv.sources]
core = { workspace = true }
TOML
  cat > "$tmp/$dfpath"
  out=$( cd "$tmp" && "$bin" 2>&1 ); got=$?
  if [ "$got" = "$want" ]; then
    pass=$((pass + 1))
  else
    fail=$((fail + 1))
    printf 'FAIL (want=%s got=%s): %s\n%s\n' "$want" "$got" "$name" "$out"
  fi
  rm -rf "$tmp"
}

CORE_TOML='COPY packages/core/pyproject.toml packages/core/pyproject.toml'

# Directory-copied dependency passes.
check 0 'dir copy' apps/api/Dockerfile <<'EOF'
FROM scratch
COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY packages/core/pyproject.toml packages/core/pyproject.toml
COPY packages/core packages/core
COPY apps/api apps/api
RUN uv sync --frozen --no-dev --package api
EOF

# Manifest-only copy is the hole this gate exists for: resolution works,
# the install fails with "Distribution not found".
check 1 'manifest-only copy' apps/api/Dockerfile <<EOF
FROM scratch
COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/pyproject.toml
$CORE_TOML
COPY apps/api apps/api
RUN uv sync --frozen --no-dev --package api
EOF

# Dependency never copied fails.
check 1 'dep not copied' apps/api/Dockerfile <<'EOF'
FROM scratch
COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY apps/api apps/api
RUN uv sync --frozen --no-dev --package api
EOF

# A copy into the package path (dest side) does not provide the source.
check 1 'dest-only mention' apps/api/Dockerfile <<'EOF'
FROM scratch
COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY README.md packages/core
COPY apps/api apps/api
RUN uv sync --frozen --no-dev --package api
EOF

# Build stages share the context: an early-stage COPY does provide it,
# but a --from copy of an unrelated stage path satisfies nothing.
check 0 'early-stage context copy counts' apps/api/Dockerfile <<'EOF'
FROM scratch AS build
COPY packages/core packages/core
FROM scratch
COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY --from=build /app/packages/core /app/packages/core
COPY apps/api apps/api
RUN uv sync --frozen --no-dev --package api
EOF

# JSON-form copy counts.
check 0 'json dir copy' apps/api/Dockerfile <<'EOF'
FROM scratch
COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY ["packages/core/pyproject.toml", "packages/core/pyproject.toml"]
COPY ["packages/core", "packages/core"]
COPY apps/api apps/api
RUN uv sync --frozen --no-dev --package api
EOF

# Continued COPY line counts.
check 0 'continued copy line' apps/api/Dockerfile <<'EOF'
FROM scratch
COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY packages/core/pyproject.toml \
     packages/core/pyproject.toml
COPY packages/core packages/core
COPY apps/api apps/api
RUN uv sync --frozen --no-dev --package api
EOF

# A package that is not a dependency may stay out of the image.
check 0 'non-dependency package uncopied' apps/api/Dockerfile <<'EOF'
FROM scratch
COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY packages/core/pyproject.toml packages/core/pyproject.toml
COPY packages/core packages/core
COPY apps/api apps/api
RUN uv sync --frozen --no-dev --package api
EOF

# No uv sync: completeness does not apply.
check 0 'no uv sync' apps/api/Dockerfile <<'EOF'
FROM scratch
COPY apps/api apps/api
CMD ["true"]
EOF

# Whole-workspace syncs (non-app Dockerfile) still need every package.
check 1 'root sync missing package' docker/build/Dockerfile <<'EOF'
FROM scratch
COPY pyproject.toml uv.lock ./
COPY packages/core/pyproject.toml packages/core/pyproject.toml
COPY packages/core packages/core
RUN uv sync --frozen
EOF

printf 'check-docker tests: %s passed, %s failed\n' "$pass" "$fail"
[ "$fail" = 0 ]
