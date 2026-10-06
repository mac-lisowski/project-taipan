# Current state

- Branch: `feat/config-session-store`.
- Validated finding: env parsing scattered, no central config, and no session store port before Redis adoption.
- Built `api.config` (eager validation, fail-loud) and `api.session_store` (port with Memory and Redis adapters).
- Rewired `db.py`, `field_crypto.py`, and `conftest.py` through `api.config`.
- Next: review and commit.
