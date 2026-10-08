"""Mail composition root: pick the email adapter once from server config."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from email_delivery import (
    EmailSender,
    FakeEmailSender,
    GuardedEmailSender,
    MemorySuppressionStore,
    PostgresSuppressionStore,
    ResendEmailSender,
    SuppressionStore,
)
from email_delivery.resend import EmailTransport
from fastapi import Request

from api.config import Config, get_config

# One home for the app name in mail; a rename touches this line only.
APP_NAME = "Taipan"


def build_email_sender(
    config: Config | None = None,
    *,
    transport: EmailTransport | None = None,
    session_factory: Callable[[], Any] | None = None,
) -> EmailSender:
    """Build the sender once at composition time from server config.

    No key selects the fake adapter (local dev default: mail is
    captured in memory, nothing leaves the box). A key selects the
    Resend adapter for prod. Real mail never sends without a key.
    Either adapter sits behind the guard, so suppression and send
    bounds run on every composed send.
    """
    cfg = config or get_config()
    if not cfg.mail.resend_api_key:
        inner: EmailSender = FakeEmailSender()
    else:
        inner = ResendEmailSender(
            api_key=cfg.mail.resend_api_key,
            from_address=cfg.mail.mail_from_address,
            transport=transport,
        )
    store: SuppressionStore
    if session_factory is not None:
        store = PostgresSuppressionStore(session_factory)
    else:
        store = MemorySuppressionStore()
    return GuardedEmailSender(inner, store)


def get_email_sender(request: Request) -> EmailSender:
    """Route dependency. App code receives the interface only."""
    return request.app.state.email_sender
