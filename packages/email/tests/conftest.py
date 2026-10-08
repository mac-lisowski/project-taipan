"""Parametrized store leg for the suppression suite: memory and Postgres.

The Postgres leg runs on the app_test database and skips when Postgres
is unreachable, the same convention as the live KV store tests.
Constants and helpers live in email_testsupport.py.
"""

import pytest
from email_delivery.suppression import (
    MemorySuppressionStore,
    PostgresSuppressionStore,
    SuppressionStore,
)
from email_testsupport import _BACKENDS, _TABLES_DDL, TEST_DB_URL


@pytest.fixture(params=_BACKENDS)
def store(request: pytest.FixtureRequest) -> SuppressionStore:
    if request.param == "memory":
        yield MemorySuppressionStore()
        return
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(TEST_DB_URL)
    with engine.begin() as conn:
        conn.execute(text(_TABLES_DDL))
        for table in ("email_webhook_events", "email_send_counters", "email_suppressions"):
            conn.execute(text(f"DELETE FROM {table}"))
    yield PostgresSuppressionStore(sessionmaker(bind=engine, expire_on_commit=False))
    with engine.begin() as conn:
        for table in ("email_webhook_events", "email_send_counters", "email_suppressions"):
            conn.execute(text(f"DELETE FROM {table}"))
    engine.dispose()
