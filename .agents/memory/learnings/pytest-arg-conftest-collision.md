# Explicit pytest args used to break conftest imports

`uv run pytest packages apps/api -q` used to die in collection: 17
ImportErrors, every `from conftest import X` resolving to
packages/kms/tests/conftest.py. Bare `uv run pytest` (testpaths) was
green only because apps/api/tests loaded last.

- All tests dirs lack `__init__.py`, so every conftest.py competes
  for the single bare module name `conftest`; a test module importing
  it got whichever conftest loaded last.
- FIXED 2026-10-08 (92f41f3): helpers moved to uniquely named support
  modules (api_testsupport.py, email_testsupport.py); conftest.py
  keeps only fixtures; no test module imports the bare name.
- Rule: keep shared test helpers in distinctly named support modules.
  Never `from conftest import X` in a test module.
