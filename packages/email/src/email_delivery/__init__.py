"""Email delivery seam: one sender interface, fake adapter for dev/tests."""

from email_delivery.fake import FakeEmailSender
from email_delivery.resend import ResendEmailSender, ResendError
from email_delivery.resend_events import (
    ALL_EVENT_TYPES,
    DEFAULT_BOUNCE_SUBTYPE,
    ResendEventType,
    bounce_kind_for,
)
from email_delivery.sender import (
    EmailSender,
    SendResult,
    SendStatus,
    SentEmail,
)
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

__all__ = [
    "ALL_EVENT_TYPES",
    "DEFAULT_BOUNCE_SUBTYPE",
    "MAX_SENDS_PER_RECIPIENT",
    "MAX_SENDS_PER_RECIPIENT_TEMPLATE",
    "MAX_SOFT_BOUNCES",
    "BounceKind",
    "EmailSender",
    "FakeEmailSender",
    "GuardedEmailSender",
    "MemorySuppressionStore",
    "PostgresSuppressionStore",
    "ResendEmailSender",
    "ResendError",
    "ResendEventType",
    "SendResult",
    "SendStatus",
    "SentEmail",
    "SuppressionStore",
    "bounce_kind_for",
]
