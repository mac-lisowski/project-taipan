# Current state

- Worktree ../project-taipan-litellm, branch feat/litellm-gateway-docker
  (cut from dev 8f42ac4). ALL WORK UNCOMMITTED, gated on user approval.
- litellm-gateway-docker spec IMPLEMENTED: docker/litellm/Dockerfile
  (pull-through v1.104.0), litellm + litellm-db in both compose stacks
  (host publishes 4000, devcontainer none, volumes litellm-pgdata /
  devcontainer-litellm-pgdata), README + docs/devcontainer.md +
  .devcontainer/README.md updated. Tickets 01+02 done with HTML
  reports in .scratch/litellm-gateway-docker/issues/.
- Ticket 03 (user-directed): CI deploy job gains gated
  `deploy litellm` step mirroring deploy infisical. Focused review
  pass clean; YAML parses; 271/300 lines.
- Ticket 04 (user-directed): deploy inputs moved to environment
  secrets. GitHub env project-taipan / dev now holds 6 secrets
  (RAILWAY_TOKEN, RAILWAY_PROJECT_ID, RAILWAY_ENVIRONMENT,
  RAILWAY_SERVICE_WEB/API/INFISICAL), 0 vars; old vars deleted.
  ci.yml deploy job reads secrets.* everywhere; gates too.
  RAILWAY_SERVICE_LITELLM deliberately NOT set at ticket time;
  set 2026-10-08 (user created the Railway service, id
  1c887eb8-19b9-4e80-99e7-c56d132a0d48). Env now holds 7 secrets,
  0 vars; litellm deploy gate opens on first dev push carrying this
  branch. Still manual on Railway: Dockerfile builder setting +
  DATABASE_URL (Railway Postgres) + LITELLM_MASTER_KEY /
  LITELLM_SALT_KEY / STORE_MODEL_IN_DB on the service.
  gh --env flag 404s on
  this env name (space/space encoding bug); used raw API +
  pynacl sealed box (learnings/gh-env-name-encoding.md).
- Verification: both compose configs pass, check-docker.sh passes,
  image builds, live bring-up on project-taipan-litellm compose
  project (still running, port 4000 only): liveliness "I'm alive!",
  keyless 401, master-key 400 model-problem, /ui 307, model survives
  --force-recreate. pytest 379 passed 9 skipped (pre-existing skips).
- Deviation from spec text (documented, decision
  decisions/litellm-dev-keys.md): master key dev default is
  sk-taipan-dev-4f8a2c91e6b3d705, NOT spec's sk-1234, because
  v1.104.0 refuses to boot on publicly-known keys. Salt default
  sk-taipan-salt-9b1c64e2a8d3f704. No dangerous-permit flag.
- code-review two-axis CLEAN on 01+02 (Standards: 4 judgement calls,
  none blocking; Spec: all criteria met). 03 hunk-reviewed clean.
- Next: user approves -> review-stamp.sh -> conventional commits
  (feat: litellm gateway docker stack #<spec num>) -> spec to
  docs/specs/implemented/ per implement-spec step 8. Railway side
  stays manual: create service (Dockerfile builder =
  docker/litellm/Dockerfile) + Postgres + vars, then add env secret
  RAILWAY_SERVICE_LITELLM (GitHub web UI - gh --env is broken for
  this env name). Stack down: docker compose down in the worktree
  (keeps volume).
