"""Suppression conformance: memory and Postgres stores behave the same.

One behavior per test, asserted through the guard. The store legs
live in conftest.py; guard and address helpers in email_testsupport.py.
"""

from email_delivery.sender import SendStatus
from email_delivery.suppression import (
    MAX_SENDS_PER_RECIPIENT,
    MAX_SENDS_PER_RECIPIENT_TEMPLATE,
    MAX_SOFT_BOUNCES,
    BounceKind,
    PostgresSuppressionStore,
    SuppressionStore,
)
from email_testsupport import _TABLES_DDL, TEST_DB_URL, _address, _guarded, needs_postgres


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

    early = [guarded.record_bounce(recipient, BounceKind.SOFT) for _ in range(MAX_SOFT_BOUNCES - 1)]
    assert early == [False] * (MAX_SOFT_BOUNCES - 1)
    result = guarded.send("activation", recipient, {"link": "https://x/y"})

    assert result.status is SendStatus.SENT
    assert len(inner.list_sent()) == 1


def test_third_soft_bounce_suppresses(store: SuppressionStore) -> None:
    inner, guarded = _guarded(store)
    recipient = _address()

    early = [guarded.record_bounce(recipient, BounceKind.SOFT) for _ in range(MAX_SOFT_BOUNCES - 1)]
    assert early == [False] * (MAX_SOFT_BOUNCES - 1)
    assert guarded.record_bounce(recipient, BounceKind.SOFT) is True
    result = guarded.send("reset", recipient, {"link": "https://x/y"})

    assert store.is_suppressed(recipient) is True
    assert result.status is SendStatus.SUPPRESSED
    assert inner.list_sent() == []


def test_repeat_soft_bounce_event_id_counts_once(store: SuppressionStore) -> None:
    inner, guarded = _guarded(store)
    recipient = _address()
    # Fixed id: dedup is the behavior under test; a constant keeps failures reproducible.
    event_id = "evt-repeat-soft"

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
    event_id = "evt-repeat-hard"

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
