# uv workspace glob matches apps/web

`members = ["apps/*"]` matches apps/web (no pyproject.toml).
`uv sync --frozen` passes but `uv run` fails: "workspace member is
missing a pyproject.toml". Fix is `exclude = ["apps/web"]` under
`[tool.uv.workspace]`.
