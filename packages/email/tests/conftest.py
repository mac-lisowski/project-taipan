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
from email_testsupport import BACKENDS, TEST_DB_URL, init_tables, reset_tables


@pytest.fixture(params=BACKENDS)
def store(request: pytest.FixtureRequest) -> SuppressionStore:
    if request.param == "memory":
        yield MemorySuppressionStore()
        return
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(TEST_DB_URL)
    init_tables(engine)
    yield PostgresSuppressionStore(sessionmaker(bind=engine, expire_on_commit=False))
    reset_tables(engine)
    engine.dispose()
