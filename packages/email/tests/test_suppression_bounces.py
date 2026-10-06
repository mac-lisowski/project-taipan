"""Suppression, bounce stance, and send bounds (ticket 04)."""

from email_delivery import FakeEmailSender
from email_delivery.suppression import (
    MAX_SENDS_PER_RECIPIENT,
    MAX_SENDS_PER_RECIPIENT_TEMPLATE,
    MAX_SOFT_BOUNCES,
    BounceKind,
    GuardedEmailSender,
    MemorySuppressionStore,
    guarded_send,
)


def _guarded() -> tuple[FakeEmailSender, GuardedEmailSender]:
    inner = FakeEmailSender()
    return inner, GuardedEmailSender(inner, MemorySuppressionStore())


def test_suppressed_address_short_circuits_with_no_vendor_call() -> None:
    inner, guarded = _guarded()
    guarded.store.suppress("ada@example.com")

    result = guarded.send("activation", "ada@example.com", {"link": "https://x/y"})

    assert result.status.value == "suppressed"
    assert inner.list_sent() == []


def test_suppression_checked_before_render() -> None:
    inner, guarded = _guarded()
    guarded.store.suppress("ada@example.com")

    result = guarded_send(guarded, "activation", "ada@example.com", {"bad": "data"})

    assert result.status.value == "suppressed"
    assert inner.list_sent() == []


def test_suppression_key_is_case_insensitive() -> None:
    store = MemorySuppressionStore()
    store.suppress("Ada@Example.COM")

    assert store.is_suppressed("ada@example.com") is True


def test_hard_bounce_suppresses_repeat_send() -> None:
    inner, guarded = _guarded()

    guarded.record_bounce("ada@example.com", BounceKind.HARD)
    result = guarded.send("activation", "ada@example.com", {"link": "https://x/y"})

    assert result.status.value == "suppressed"
    assert inner.list_sent() == []


def test_soft_bounces_below_bound_still_send() -> None:
    inner, guarded = _guarded()

    for _ in range(MAX_SOFT_BOUNCES - 1):
        guarded.record_bounce("ada@example.com", BounceKind.SOFT)

    result = guarded.send("activation", "ada@example.com", {"link": "https://x/y"})

    assert result.status.value == "sent"
    assert len(inner.list_sent()) == 1


def test_soft_bounce_at_bound_suppresses() -> None:
    inner, guarded = _guarded()

    for _ in range(MAX_SOFT_BOUNCES):
        guarded.record_bounce("bob@example.com", BounceKind.SOFT)

    assert guarded.store.is_suppressed("bob@example.com") is True
    result = guarded.send("reset", "bob@example.com", {"link": "https://x/y"})

    assert result.status.value == "suppressed"
    assert inner.list_sent() == []


def test_excess_sends_per_recipient_reject_with_retryable_reason() -> None:
    inner, guarded = _guarded()

    results = [
        guarded.send(f"template-{i % 4}", "ada@example.com", {"n": i})
        for i in range(MAX_SENDS_PER_RECIPIENT)
    ]
    assert len(results) == MAX_SENDS_PER_RECIPIENT
    assert all(r.status.value == "sent" for r in results)

    result = guarded.send("activation", "ada@example.com", {"link": "https://x/y"})

    assert result.status.value == "failed"
    assert "retry" in result.reason
    assert len(inner.list_sent()) == MAX_SENDS_PER_RECIPIENT


def test_excess_sends_per_recipient_template_reject_with_retryable_reason() -> None:
    inner, guarded = _guarded()

    results = [
        guarded.send("activation", "ada@example.com", {"n": i})
        for i in range(MAX_SENDS_PER_RECIPIENT_TEMPLATE)
    ]
    assert len(results) == MAX_SENDS_PER_RECIPIENT_TEMPLATE
    assert all(r.status.value == "sent" for r in results)

    result = guarded.send("activation", "ada@example.com", {"n": "extra"})

    assert result.status.value == "failed"
    assert "retry" in result.reason
    assert len(inner.list_sent()) == MAX_SENDS_PER_RECIPIENT_TEMPLATE
