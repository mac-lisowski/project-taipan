# python-playground

A Python monorepo managed with [uv workspaces](https://docs.astral.sh/uv/concepts/workspaces/).
Shared libraries live in `packages/`, runnable applications live in `apps/`.

```
├── pyproject.toml        # workspace root: members, shared dev tools
├── packages/
│   └── core/             # library: core
└── apps/
    ├── cli/              # app: cli (depends on core)
    └── api/              # app: api (depends on core)
```

## Everyday commands

Run from the repo root - one lockfile, one virtualenv for everything:

```bash
uv sync                    # install/update everything into .venv
uv run pytest              # run all tests across all packages
uv run ruff check .        # lint everything

uv add --package core requests   # add a dep to one member
uv add pytest --dev                          # add a shared dev dependency
```

## Run the apps

Each app registers a command in its `pyproject.toml` under `[project.scripts]`.

```bash
uv run cli                 # CLI app -> prints "Hello, world!"
uv run api                 # API app -> FastAPI server on http://127.0.0.1:8000 (docs at /docs)
```

## Adding a new project

1. Create `packages/<name>/` (library) or `apps/<name>/` (application) with a
   `pyproject.toml` and `src/<import_name>/__init__.py` - copy an existing one.
2. Add it to the root `pyproject.toml` dependencies + `[tool.uv.sources]`
   (`<name> = { workspace = true }`).
3. To depend on another workspace member, do the same in your project's
   `pyproject.toml`.
4. `uv sync`.

## Conventions

- `src/` layout per package (import from `packages/core/src/core`).
- Tests live in each package under `tests/`.
- Python version pinned in `.python-version`; lockfile is `uv.lock`.
