# Explicit pytest args break conftest imports

`uv run pytest packages apps/api -q` dies in collection: 17
ImportErrors, every `from conftest import X` resolving to
packages/kms/tests/conftest.py. Bare `uv run pytest` (testpaths
`["packages", "apps"]`) is green and collects the same tests.

- All tests dirs lack `__init__.py`, so every conftest.py competes
  for the single bare module name `conftest`; which one a test file
  gets depends on load order.
- Under testpaths the last loader is apps/api/tests/conftest.py, so
  apps/api's `from conftest import ALEMBIC_INI` resolves right.
- Explicit arg order does not reproduce that luck. Reproduced on a
  clean dev checkout (f901488), so it is not caused by recent edits;
  the exact order difference was not diagnosed.
- Remedy: run bare `uv run pytest`. Keep per-suite helpers in
  distinctly named support modules (see api_testsupport.py) instead
  of growing conftest imports.
