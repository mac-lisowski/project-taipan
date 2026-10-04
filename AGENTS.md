# AGENTS.md

## Rules

1. Keep all output short. Follow STE100 (Simplified Technical English):
   short sentences, simple words, one idea per sentence. No essays.
   No em dashes.
2. Do not edit generated scaffold files unless asked.
3. Use `uv run <cmd>` for all commands. Never activate `.venv` manually.
4. Memory lives in `.agents/memory/`. Read `current.md` before a task.
   Update memory files per `.agents/memory/MEMORY.md` rules.

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
docs/learnings/           study notes
.agents/memory/           agent memory across sessions
```

Naming rule: folder `packages/core` = package `core` (in `dependencies` +
`[tool.uv.sources]`) = module `core` (dir in `src/`, used in `import`).
All three use the same generic name, no repo prefix.

## Commands

```bash
uv sync                 # install all workspace members into .venv
uv run pytest           # run all tests
uv run ruff check .     # lint
uv run cli              # run the cli app
uv run api              # run the api app
uv add --package <pkg> <dep>   # add dep to one member
uv add <dep> --dev             # add shared dev dep
```

## Adding a project

1. Copy `packages/core` or `apps/cli` to `packages/<name>` or `apps/<name>`.
2. Rename package in its `pyproject.toml`; rename `src/` dir (underscores).
3. Add to root `pyproject.toml`: `dependencies` + `uv.sources`.
4. `uv sync`.
