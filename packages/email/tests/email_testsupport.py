"""Shared constants and helpers for the suppression suite.

Helpers live here, not in conftest, so test modules never import the
bare name `conftest` (every tests dir's conftest competes for that
one module name; importing it is collection-order luck).
"""

import os
import uuid

import pytest
from email_delivery import FakeEmailSender
from email_delivery.suppression import GuardedEmailSender, SuppressionStore

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


def _guarded(store: SuppressionStore) -> tuple[FakeEmailSender, GuardedEmailSender]:
    inner = FakeEmailSender()
    return inner, GuardedEmailSender(inner, store)


def _address() -> str:
    return f"user-{uuid.uuid4().hex}@example.com"
