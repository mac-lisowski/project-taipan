# AGENTS.md

## Rules

1. Keep all output short. Follow STE100 (Simplified Technical English):
   short sentences, simple words, one idea per sentence. No essays.
2. Do not edit generated scaffold files unless asked.
3. Use `uv run <cmd>` for all commands. Never activate `.venv` manually.

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
```

Naming rule: folder `packages/core` → package `playground-core` (hyphens,
in `dependencies` + `[tool.uv.sources]`) → module `playground_core`
(underscores, used in `import`).

## Commands

```bash
uv sync                 # install all workspace members into .venv
uv run pytest           # run all tests
uv run ruff check .     # lint
uv run playground       # run the cli app
uv add --package <pkg> <dep>   # add dep to one member
uv add <dep> --dev             # add shared dev dep
```

## Adding a project

1. Copy `packages/core` or `apps/cli` to `packages/<name>` or `apps/<name>`.
2. Rename package in its `pyproject.toml`; rename `src/` dir (underscores).
3. Add to root `pyproject.toml`: `dependencies` + `uv.sources`.
4. `uv sync`.
