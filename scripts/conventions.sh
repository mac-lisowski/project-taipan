#!/usr/bin/env bash
# Single source for commit and branch conventions.
# Sourced by scripts/check-*.sh and scripts/tests/*.sh - never executed.
# Add a type or generic scope here once; hooks, CI, and tests pick it up.
# docs/commit-convention.md mirrors these lists; scripts/tests/test-branch-name.sh
# fails when the doc drifts.
TAIPAN_TYPES='feat fix docs style refactor perf test build ci chore revert'
TAIPAN_GENERIC_SCOPES='repo ci docs deps scripts evals docker devcontainer agents hooks github'
