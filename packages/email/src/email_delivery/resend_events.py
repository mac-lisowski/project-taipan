"""Resend webhook event registry. Single source for provider strings.

Names mirror the official SDK `WebhookEvent` list
(resend-python `resend/webhooks/_webhook.py`).
The mapping to bounce handling is ours; the SDK ships names only.
"""

from enum import Enum

from email_delivery.suppression import BounceKind


class ResendEventType(str, Enum):
    """Every event type Resend can deliver to a webhook."""

    BOUNCED = "email.bounced"
    CLICKED = "email.clicked"
    COMPLAINED = "email.complained"
    DELIVERED = "email.delivered"
    DELIVERY_DELAYED = "email.delivery_delayed"
    FAILED = "email.failed"
    OPENED = "email.opened"
    RECEIVED = "email.received"
    SCHEDULED = "email.scheduled"
    SENT = "email.sent"
    SUPPRESSED = "email.suppressed"
    CONTACT_CREATED = "contact.created"
    CONTACT_UPDATED = "contact.updated"
    CONTACT_DELETED = "contact.deleted"
    CONTACT_TOPICS_UPDATED = "contact.topics.updated"
    DOMAIN_CREATED = "domain.created"
    DOMAIN_UPDATED = "domain.updated"
    DOMAIN_DELETED = "domain.deleted"
    SUPPRESSION_ADDED = "suppression.added"
    SUPPRESSION_REMOVED = "suppression.removed"
    TOPIC_CREATED = "topic.created"
    TOPIC_UPDATED = "topic.updated"
    TOPIC_DELETED = "topic.deleted"


ALL_EVENT_TYPES: tuple[str, ...] = tuple(e.value for e in ResendEventType)

_BOUNCE_SUBTYPES = {"hard": BounceKind.HARD, "soft": BounceKind.SOFT}

# Absent subtype treats as hard. Missing data fails toward suppression.
DEFAULT_BOUNCE_SUBTYPE = "hard"


def bounce_kind_for(event_type: str, subtype: str = "hard") -> BounceKind | None:
    """Map a provider event to a bounce kind. None means ignore.

    Bounced needs the payload subtype; complaint maps directly.
    Unknown types (including future provider additions) ignore safely.
    """
    if event_type == ResendEventType.BOUNCED:
        return _BOUNCE_SUBTYPES.get(subtype)
    if event_type == ResendEventType.COMPLAINED:
        return BounceKind.COMPLAINT
    return None
