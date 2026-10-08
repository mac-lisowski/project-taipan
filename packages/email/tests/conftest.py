"""Shared plumbing for the suppression suite: the parametrized store leg.

The Postgres leg runs on the app_test database and skips when Postgres
is unreachable, the same convention as the live KV store tests.
"""

import os
import uuid

import pytest
from email_delivery import FakeEmailSender
from email_delivery.suppression import (
    GuardedEmailSender,
    MemorySuppressionStore,
    PostgresSuppressionStore,
    SuppressionStore,
)

TEST_DB_URL = os.environ.get(
    "API_TEST_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/app_test",
)

# Mirrors the ticket 01 migration DDL; this suite owns its tables.
_TABLES_DDL = """
CREATE TABLE IF NOT EXISTS email_suppressions (
    address TEXT PRIMARY KEY,
    reason TEXT NOT NULL
        CHECK (reason IN ('hard', 'soft-limit', 'complaint')),
    soft_bounces INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS email_send_counters (
    recipient TEXT NOT NULL,
    template TEXT NOT NULL,
    sent_count BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (recipient, template)
);
CREATE TABLE IF NOT EXISTS email_webhook_events (
    event_id TEXT PRIMARY KEY,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def _postgres_reachable() -> bool:
    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.exc import SQLAlchemyError
    except ImportError:
        return False
    try:
        engine = create_engine(TEST_DB_URL, connect_args={"connect_timeout": 2})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except SQLAlchemyError:
        return False


POSTGRES_UP = _postgres_reachable()
needs_postgres = pytest.mark.skipif(not POSTGRES_UP, reason="postgres not reachable")


# Reachable backends only; without Postgres the memory leg still proves behavior.
_BACKENDS = ["memory", "postgres"] if POSTGRES_UP else ["memory"]


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


def _guarded(store: SuppressionStore) -> tuple[FakeEmailSender, GuardedEmailSender]:
    inner = FakeEmailSender()
    return inner, GuardedEmailSender(inner, store)


def _address() -> str:
    return f"user-{uuid.uuid4().hex}@example.com"
