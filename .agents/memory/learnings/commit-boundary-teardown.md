# Request commit happens in the get_db teardown

- `api/db.py` `get_db`: `yield db; db.commit()` runs after the endpoint
  returns. Pinned by `tests/test_commit_boundary.py`.
- "After commit" or "on commit failure" ordering claims are not
  executable at endpoint level.
- Patterns that work: `db.commit()` inside the service
  (`chat/complete.py` `_persist`), `session.flush()` in try/except,
  or a Session `after_commit` event.
- Any spec saying "object write after commit" needs one of these
  named explicitly.
