# Current state

- Branch feat/litellm-gateway-docker PUSHED, PR #36 open to dev
  (https://github.com/mac-lisowski/project-taipan/pull/36). Commit
  c377f71 feat: litellm gateway docker stack; docs commit marks spec
  implemented (PR #36). Tickets 01-04 done with HTML reports in
  .scratch/litellm-gateway-docker/issues/.
- litellm-gateway-docker IMPLEMENTED: docker/litellm/Dockerfile
  (pull-through v1.104.0), litellm + litellm-db in both compose stacks
  (host publishes 4000, devcontainer none, volumes litellm-pgdata /
  devcontainer-litellm-pgdata), README + docs/devcontainer.md +
  .devcontainer/README.md updated, CI deploy job gated
  `deploy litellm` step, ALL deploy inputs as GitHub env secrets
  (project-taipan / dev: 7 secrets, 0 vars).
- Dev keys deviation (decisions/litellm-dev-keys.md): committed dev
  defaults sk-taipan-dev-4f8a2c91e6b3d705 (master) /
  sk-taipan-salt-9b1c64e2a8d3f704 (salt), because v1.104.0 refuses
  publicly-known keys like spec's sk-1234.
- User did the Railway side 2026-10-08: litellm service
  (1c887eb8-19b9-4e80-99e7-c56d132a0d48), Postgres + DATABASE_URL,
  master/salt keys, STORE_MODEL_IN_DB. RAILWAY_SERVICE_LITELLM secret
  set by me. Gateway deploys on the first dev push carrying this
  branch (merge).
- Verification on record: compose configs + check-docker pass, image
  builds, live host stack liveliness/401/master-key//ui, model
  persists across --force-recreate, pytest 379 passed 9 skipped,
  code-review two-axis CLEAN (01+02), focused passes clean (03+04).
- Next after merge: on dev, git mv docs/specs/planned/litellm-gateway-docker
  docs/specs/implemented/ (password-change precedent, separate docs
  commit); verify CI deploy job runs litellm; then worktree
  ../project-taipan-litellm and branch deletable.
