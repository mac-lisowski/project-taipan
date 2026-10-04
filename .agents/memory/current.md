# Current state

- Last updated: 2026-10-04
- Active work: devcontainer done (.devcontainer/: app + db + dind,
  root user for rootless Docker, conftest reads API_TEST_* env vars).
  Verified: pytest, db-upgrade, api, testcontainers all pass inside.
- Next step: move conftest to testcontainers, or more entities
- Blockers: host port 5432 taken by python-playground-db-1; root
  docker-compose.yaml db cannot publish while it runs
