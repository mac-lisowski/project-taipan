"""Resend event registry: every provider string lives here, not in callers."""

from email_delivery.resend_events import (
    ALL_EVENT_TYPES,
    ResendEventType,
    bounce_kind_for,
)
from email_delivery.suppression import BounceKind


def test_registry_matches_the_sdk_catalog() -> None:
    """Drift tripwire: our names must equal the SDK WebhookEvent list."""
    from typing import get_args

    from resend import WebhookEvent

    assert {e.value for e in ResendEventType} == set(get_args(WebhookEvent))
    assert set(ALL_EVENT_TYPES) == set(get_args(WebhookEvent))


def test_bounced_maps_through_payload_subtype() -> None:
    assert bounce_kind_for("email.bounced", "hard") == BounceKind.HARD
    assert bounce_kind_for("email.bounced", "soft") == BounceKind.SOFT
    assert bounce_kind_for("email.bounced", "fuzzy") is None


def test_complaint_maps_directly() -> None:
    assert bounce_kind_for("email.complained") == BounceKind.COMPLAINT


def test_non_suppressing_events_are_ignored() -> None:
    for event_type in (
        "email.sent",
        "email.delivered",
        "email.opened",
        "contact.created",
        "suppression.added",
    ):
        assert bounce_kind_for(event_type) is None
    assert bounce_kind_for("email.unknown-future-type") is None
