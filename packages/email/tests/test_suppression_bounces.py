"""Suppression conformance: memory and Postgres stores behave the same.

One behavior per test, asserted through the guard. The Postgres leg
runs on the app_test database and skips when Postgres is unreachable,
the same convention as the live KV store tests.
"""

import os
import uuid

import pytest
from email_delivery import FakeEmailSender
from email_delivery.sender import SendResult, SendStatus
from email_delivery.suppression import (
    MAX_SENDS_PER_RECIPIENT,
    MAX_SENDS_PER_RECIPIENT_TEMPLATE,
    MAX_SOFT_BOUNCES,
    BounceKind,
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


def test_bounds_match_spec_values() -> None:
    assert MAX_SENDS_PER_RECIPIENT == 100
    assert MAX_SENDS_PER_RECIPIENT_TEMPLATE == 50
    assert MAX_SOFT_BOUNCES == 3


def test_suppress_short_circuits_send_with_no_vendor_call(
    store: SuppressionStore,
) -> None:
    inner, guarded = _guarded(store)
    recipient = _address()
    store.suppress(recipient)

    result = guarded.send("activation", recipient, {"link": "https://x/y"})

    assert result.status is SendStatus.SUPPRESSED
    assert inner.list_sent() == []


def test_suppression_checked_before_render(store: SuppressionStore) -> None:
    inner, guarded = _guarded(store)
    recipient = _address()
    store.suppress(recipient)

    result = guarded.send("activation", recipient, {"bad": "data"})

    assert result.status is SendStatus.SUPPRESSED
    assert inner.list_sent() == []


def test_suppression_key_is_case_insensitive(store: SuppressionStore) -> None:
    store.suppress("Ada@Example.COM")

    assert store.is_suppressed("ada@example.com") is True


def test_hard_bounce_suppresses_repeat_send(store: SuppressionStore) -> None:
    inner, guarded = _guarded(store)
    recipient = _address()

    suppressed_now = guarded.record_bounce(recipient, BounceKind.HARD)
    result = guarded.send("activation", recipient, {"link": "https://x/y"})

    assert suppressed_now is True
    assert result.status is SendStatus.SUPPRESSED
    assert inner.list_sent() == []


def test_complaint_bounce_suppresses_repeat_send(store: SuppressionStore) -> None:
    inner, guarded = _guarded(store)
    recipient = _address()

    suppressed_now = guarded.record_bounce(recipient, BounceKind.COMPLAINT)
    result = guarded.send("activation", recipient, {"link": "https://x/y"})

    assert suppressed_now is True
    assert result.status is SendStatus.SUPPRESSED
    assert inner.list_sent() == []


def test_soft_bounces_below_bound_still_send(store: SuppressionStore) -> None:
    inner, guarded = _guarded(store)
    recipient = _address()

    for _ in range(MAX_SOFT_BOUNCES - 1):
        assert guarded.record_bounce(recipient, BounceKind.SOFT) is False
    result = guarded.send("activation", recipient, {"link": "https://x/y"})

    assert result.status is SendStatus.SENT
    assert len(inner.list_sent()) == 1


def test_third_soft_bounce_suppresses(store: SuppressionStore) -> None:
    inner, guarded = _guarded(store)
    recipient = _address()

    for _ in range(MAX_SOFT_BOUNCES - 1):
        assert guarded.record_bounce(recipient, BounceKind.SOFT) is False
    assert guarded.record_bounce(recipient, BounceKind.SOFT) is True
    result = guarded.send("reset", recipient, {"link": "https://x/y"})

    assert store.is_suppressed(recipient) is True
    assert result.status is SendStatus.SUPPRESSED
    assert inner.list_sent() == []


def test_excess_sends_per_recipient_reject_with_retryable_reason(
    store: SuppressionStore,
) -> None:
    inner, guarded = _guarded(store)
    recipient = _address()

    sends = [guarded.send(f"template-{i % 4}", recipient, {"n": i}) for i in range(100)]
    assert all(r.status is SendStatus.SENT for r in sends)
    result = guarded.send("activation", recipient, {"link": "https://x/y"})

    assert result.status is SendStatus.FAILED
    assert "retry" in result.reason
    assert len(inner.list_sent()) == MAX_SENDS_PER_RECIPIENT


def test_excess_sends_per_recipient_template_reject_with_retryable_reason(
    store: SuppressionStore,
) -> None:
    inner, guarded = _guarded(store)
    recipient = _address()

    sends = [guarded.send("activation", recipient, {"n": i}) for i in range(50)]
    assert all(r.status is SendStatus.SENT for r in sends)
    result = guarded.send("activation", recipient, {"n": "extra"})

    assert result.status is SendStatus.FAILED
    assert "retry" in result.reason
    assert len(inner.list_sent()) == MAX_SENDS_PER_RECIPIENT_TEMPLATE


def test_failed_sends_do_not_consume_budget(store: SuppressionStore) -> None:
    class FailingInner(FakeEmailSender):
        def send(self, template: str, recipient: str, data: dict) -> SendResult:
            return SendResult(status=SendStatus.FAILED, reason="boom")

    recipient = _address()
    guarded = GuardedEmailSender(FailingInner(), store)

    for _ in range(MAX_SENDS_PER_RECIPIENT):
        assert guarded.send("activation", recipient, {"n": 1}).status is SendStatus.FAILED

    assert store.send_allowed("activation", recipient) is None


def test_repeat_soft_bounce_event_id_counts_once(store: SuppressionStore) -> None:
    inner, guarded = _guarded(store)
    recipient = _address()
    event_id = f"evt-{uuid.uuid4().hex}"

    assert guarded.record_bounce(recipient, BounceKind.SOFT, event_id=event_id) is False
    assert guarded.record_bounce(recipient, BounceKind.SOFT, event_id=event_id) is False
    assert guarded.record_bounce(recipient, BounceKind.SOFT) is False

    result = guarded.send("activation", recipient, {"link": "https://x/y"})

    assert result.status is SendStatus.SENT
    assert len(inner.list_sent()) == 1


def test_repeat_hard_bounce_event_id_returns_same_outcome(
    store: SuppressionStore,
) -> None:
    _, guarded = _guarded(store)
    recipient = _address()
    event_id = f"evt-{uuid.uuid4().hex}"

    first = guarded.record_bounce(recipient, BounceKind.HARD, event_id=event_id)
    second = guarded.record_bounce(recipient, BounceKind.HARD, event_id=event_id)

    assert first is True
    assert second is True
    assert store.is_suppressed(recipient) is True


@needs_postgres
def test_postgres_rows_carry_bounce_reasons() -> None:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(TEST_DB_URL)
    with engine.begin() as conn:
        conn.execute(text(_TABLES_DDL))
        for table in ("email_webhook_events", "email_send_counters", "email_suppressions"):
            conn.execute(text(f"DELETE FROM {table}"))
    try:
        store = PostgresSuppressionStore(sessionmaker(bind=engine, expire_on_commit=False))
        hard, complaint, soft = _address(), _address(), _address()
        store.record_bounce(hard, BounceKind.HARD)
        store.record_bounce(complaint, BounceKind.COMPLAINT)
        store.record_bounce(soft, BounceKind.SOFT)

        with engine.connect() as conn:
            rows = conn.execute(text("SELECT address, reason FROM email_suppressions"))
            reasons = dict(rows.fetchall())
    finally:
        with engine.begin() as conn:
            for table in (
                "email_webhook_events",
                "email_send_counters",
                "email_suppressions",
            ):
                conn.execute(text(f"DELETE FROM {table}"))
        engine.dispose()

    assert reasons[hard.strip().lower()] == "hard"
    assert reasons[complaint.strip().lower()] == "complaint"
    assert reasons[soft.strip().lower()] == "soft-limit"
