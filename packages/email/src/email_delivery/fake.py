"""Fake adapter: in-memory capture, no network."""

from collections.abc import Mapping
from typing import Any

from email_delivery.sender import (
    EmailSender,
    SendResult,
    SendStatus,
    SentEmail,
)


class FakeEmailSender(EmailSender):
    """Captures mail in memory for local dev and tests."""

    def __init__(self) -> None:
        self._sent: list[SentEmail] = []

    def send(self, template: str, recipient: str, data: Mapping[str, Any]) -> SendResult:
        self._sent.append(SentEmail(template=template, recipient=recipient, data=dict(data)))
        return SendResult(status=SendStatus.SENT)

    def list_sent(self) -> list[SentEmail]:
        return list(self._sent)

    def clear(self) -> None:
        self._sent.clear()
