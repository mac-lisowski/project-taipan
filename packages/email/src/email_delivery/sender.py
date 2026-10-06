"""Sender seam: one send operation, typed result."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


class SendStatus(str, Enum):
    SENT = "sent"
    SUPPRESSED = "suppressed"
    FAILED = "failed"


@dataclass(frozen=True)
class SendResult:
    status: SendStatus
    reason: str = ""


@dataclass(frozen=True)
class SentEmail:
    template: str
    recipient: str
    data: Mapping[str, Any] = field(default_factory=dict)


class EmailSender(Protocol):
    """Single seam for all outbound mail. Adapters implement this."""

    def send(self, template: str, recipient: str, data: Mapping[str, Any]) -> SendResult: ...
