# A new tests/ subdirectory imports api_testsupport for free

`apps/api/tests/chat/` is the first test subdir. Its modules do
`from api_testsupport import ...` with no local conftest and it works,
including standalone `pytest apps/api/tests/chat`.

- pytest loads parent conftest.py files before the test module, and in
  prepend import mode each conftest's basedir goes on sys.path. So
  `tests/conftest.py` puts `tests/` on sys.path before
  `tests/chat/test_*.py` imports.
- No `__init__.py` needed; do not add a shim conftest that does
  sys.path surgery.
