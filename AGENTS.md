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
docker-compose.yaml       Postgres 17 + pgvector
docker/initdb/            DB init scripts (vector extension)
evals/                    eval task specs
docs/learnings/           study notes
.agents/memory/           agent memory across sessions
.agents/skills/           local skills (e.g. taipan-world)
skills-lock.json          vendored skill versions
```

Naming rule: folder `packages/core` = package `core` (in `dependencies` +
`[tool.uv.sources]`) = module `core` (dir in `src/`, used in `import`).
All three use the same generic name, no repo prefix.

## Commands and adding a project

See `README.md`. It is the single source for the command list and the
add-a-project steps.
