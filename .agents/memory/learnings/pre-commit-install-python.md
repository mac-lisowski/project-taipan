# pre-commit install bakes INSTALL_PYTHON

`pre-commit install` bakes an absolute `INSTALL_PYTHON` into
`.git/hooks/*`. Host and devcontainer share `.git` but use different
`.venv` paths (`/home/mac/...` vs `/workspaces/...`), so whichever
side installs last breaks the other (`pre-commit not found`). Fix:
both sides need `pre-commit` on PATH for the hook's `command -v`
fallback - host: `uv tool install pre-commit`; container: symlink
`.venv/bin/pre-commit` to `/usr/local/bin` (in postCreateCommand).
