"""Send-budget conformance: per-recipient and per-template caps.

The guard counts only sends that reached the vendor, so a failing
inner sender never consumes budget. One behavior per test, asserted
through the guard against the same parametrized store as the
suppression tests.
"""

from email_delivery import FakeEmailSender
from email_delivery.sender import SendResult, SendStatus
from email_delivery.suppression import (
    MAX_SENDS_PER_RECIPIENT,
    MAX_SENDS_PER_RECIPIENT_TEMPLATE,
    GuardedEmailSender,
    SuppressionStore,
)
from email_testsupport import make_guarded, unique_address


def test_excess_sends_per_recipient_reject_with_retryable_reason(
    store: SuppressionStore,
) -> None:
    inner, guarded = make_guarded(store)
    recipient = unique_address()

    sends = [guarded.send(f"template-{i % 4}", recipient, {"n": i}) for i in range(100)]
    assert all(r.status is SendStatus.SENT for r in sends)
    result = guarded.send("activation", recipient, {"link": "https://x/y"})

    assert result.status is SendStatus.FAILED
    assert "retry" in result.reason
    assert len(inner.list_sent()) == MAX_SENDS_PER_RECIPIENT


def test_excess_sends_per_recipient_template_reject_with_retryable_reason(
    store: SuppressionStore,
) -> None:
    inner, guarded = make_guarded(store)
    recipient = unique_address()

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

    recipient = unique_address()
    guarded = GuardedEmailSender(FailingInner(), store)

    statuses = [
        guarded.send("activation", recipient, {"n": 1}).status
        for _ in range(MAX_SENDS_PER_RECIPIENT)
    ]
    assert statuses == [SendStatus.FAILED] * MAX_SENDS_PER_RECIPIENT

    assert store.send_allowed("activation", recipient) is None
