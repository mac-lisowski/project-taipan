"""Suppression, bounce stance, and send bounds around any sender."""

from collections.abc import Mapping
from enum import Enum
from typing import Any

from email_delivery.sender import (
    EmailSender,
    SendResult,
    SendStatus,
)

MAX_SOFT_BOUNCES = 3
MAX_SENDS_PER_RECIPIENT = 100
MAX_SENDS_PER_RECIPIENT_TEMPLATE = 50


class BounceKind(str, Enum):
    HARD = "hard"
    SOFT = "soft"


def _key(address: str) -> str:
    return address.strip().lower()


class MemorySuppressionStore:
    """Dev and test store behind the suppression lookup interface."""

    def __init__(self) -> None:
        self._suppressed: set[str] = set()
        self._soft_bounces: dict[str, int] = {}

    def suppress(self, address: str) -> None:
        self._suppressed.add(_key(address))

    def is_suppressed(self, address: str) -> bool:
        return _key(address) in self._suppressed

    def note_soft_bounce(self, address: str) -> int:
        key = _key(address)
        count = self._soft_bounces.get(key, 0) + 1
        self._soft_bounces[key] = count
        if count >= MAX_SOFT_BOUNCES:
            self._suppressed.add(key)
        return count


class GuardedEmailSender(EmailSender):
    """Checks suppression and bounds before delegating to the inner sender."""

    def __init__(self, inner: EmailSender, store: MemorySuppressionStore) -> None:
        self._inner = inner
        self.store = store
        self._sent_counts: dict[str, int] = {}
        self._sent_template_counts: dict[tuple[str, str], int] = {}

    def record_bounce(self, address: str, kind: BounceKind) -> None:
        if kind == BounceKind.HARD:
            self.store.suppress(address)
        else:
            self.store.note_soft_bounce(address)

    def send(self, template: str, recipient: str, data: Mapping[str, Any]) -> SendResult:
        key = _key(recipient)
        if self.store.is_suppressed(recipient):
            return SendResult(status=SendStatus.SUPPRESSED, reason="suppressed")
        if self._sent_counts.get(key, 0) >= MAX_SENDS_PER_RECIPIENT:
            return SendResult(status=SendStatus.FAILED, reason="retry later: recipient bound")
        template_key = (key, template)
        if self._sent_template_counts.get(template_key, 0) >= MAX_SENDS_PER_RECIPIENT_TEMPLATE:
            return SendResult(status=SendStatus.FAILED, reason="retry later: template bound")
        result = self._inner.send(template, recipient, data)
        if result.status == SendStatus.SENT:
            self._sent_counts[key] = self._sent_counts.get(key, 0) + 1
            self._sent_template_counts[template_key] = (
                self._sent_template_counts.get(template_key, 0) + 1
            )
        return result


def guarded_send(
    sender: GuardedEmailSender, template: str, recipient: str, data: Mapping[str, Any]
) -> SendResult:
    """Suppression pre-check that runs before any render or delegate work."""
    if sender.store.is_suppressed(recipient):
        return SendResult(status=SendStatus.SUPPRESSED, reason="suppressed")
    return sender.send(template, recipient, data)
