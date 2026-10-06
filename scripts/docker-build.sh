#!/usr/bin/env bash
# Single source for app image builds. Repo-root context is the
# convention for every apps/<name>/Dockerfile. CI calls this script;
# docs point here so the documented command cannot drift from the
# tested one.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
app=${1:?"usage: scripts/docker-build.sh <app> [tag]   (web, api)"}
exec docker build -f "apps/$app/Dockerfile" -t "${2:-taipan-$app}" .
