# AGENTS.md

## Rules

1. Keep all output short. Follow STE100 (Simplified Technical English):
   short sentences, simple words, one idea per sentence. No essays.
   No em dashes.
2. Do not edit generated scaffold files unless asked.
3. Use `uv run <cmd>` for all commands. Never activate `.venv` manually.
4. Memory lives in `.agents/memory/`. Read `current.md` before a task.
   Update memory files per `.agents/memory/MEMORY.md` rules.
5. Explain with Mermaid diagrams. When you describe a non-trivial
   solution, problem, or flow to the user, add a small Mermaid
   diagram. Keep it simple. One idea per diagram. Use them in docs
   you write too. Skip them for `.agents/memory/` entries and
   short answers.
6. Inside the devcontainer the same `uv run` commands apply. DB hosts
   come from env vars (`API_DATABASE_URL`, `API_TEST_*`). `localhost`
   defaults in code are fine; never hardcode `db`.
7. JS/TS apps (e.g. `apps/web`) use `pnpm -C apps/<name> <cmd>`. They
   are not uv workspace members.
8. Hard gates: 300 LOC per source file (`scripts/check-file-size.sh`),
   the web BFF boundary (`scripts/check-bff.sh`), and Dockerfile COPY
   sources resolving at repo root (`scripts/check-docker.sh`). All run
   in pre-commit and CI. Do not weaken them to make a check pass.

## Project map

```
pyproject.toml            workspace root: members, dev tools (pytest, ruff)
uv.lock                   lockfile, commit it
.python-version           Python 3.12
packages/<name>/          libraries
  src/<import_name>/      package code (import name = underscores)
  tests/                  package tests
apps/<name>/              runnable apps
  src/<import_name>/      app code
  tests/                  app tests
docker-compose.yaml       Postgres 17 + pgvector (host dev)
docker/initdb/            DB init scripts (vector extension)
.devcontainer/            dev container: app + db services, own compose file
docs/devcontainer.md      devcontainer guide and troubleshooting
evals/                    eval task specs
docs/learnings/           study notes
apps/<name>/AGENTS.md     nested rules for that subtree (e.g. apps/api)
CLAUDE.md                 symlink -> AGENTS.md
.claude/settings.json     hook manifest + permissions (Claude, Devin, Grok)
.zcode/config.json        ZCode hooks (hooks.enabled)
.devin/config.json        Devin permissions (no hooks: see .agents/hooks/)
.agents/memory/           agent memory across sessions
.agents/skills/           local skills (e.g. taipan-world)
.agents/commands/         slash commands (e.g. /plan)
.agents/hooks/            hook scripts wired from tool manifests
skills-lock.json          vendored skill versions
```

Naming rule: folder `packages/core` = package `core` (in `dependencies` +
`[tool.uv.sources]`) = module `core` (dir in `src/`, used in `import`).
All three use the same generic name, no repo prefix.

## Commands and adding a project

See `README.md`. It is the single source for the command list and the
add-a-project steps.
