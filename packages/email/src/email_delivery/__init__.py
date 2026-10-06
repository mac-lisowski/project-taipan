"""Email delivery seam: one sender interface, fake adapter for dev/tests."""

from email_delivery.fake import FakeEmailSender
from email_delivery.resend import ResendEmailSender, ResendError
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
    guarded_send,
)

__all__ = [
    "MAX_SENDS_PER_RECIPIENT",
    "MAX_SENDS_PER_RECIPIENT_TEMPLATE",
    "MAX_SOFT_BOUNCES",
    "BounceKind",
    "EmailSender",
    "FakeEmailSender",
    "GuardedEmailSender",
    "MemorySuppressionStore",
    "ResendEmailSender",
    "ResendError",
    "SendResult",
    "SendStatus",
    "SentEmail",
    "guarded_send",
]
