"""Resend adapter: prod delivery behind the sender seam."""

import logging
from collections.abc import Mapping
from typing import Any, Protocol

import resend

from email_delivery.sender import EmailSender, SendResult, SendStatus
from email_delivery.templates import TemplateValidationError, render

logger = logging.getLogger(__name__)


class ResendError(Exception):
    """Vendor call failed. Never carries key or token material."""


class EmailTransport(Protocol):
    """Narrow seam the sender needs. Stubs implement this, never HTTP."""

    def post_email(self, payload: dict) -> None: ...


class ResendTransport:
    """Live transport over the official SDK. Key set once per process."""

    def __init__(self, api_key: str) -> None:
        # Single process-global key: composition builds one sender.
        resend.api_key = api_key

    def post_email(self, payload: dict) -> None:
        # Any SDK failure maps to one stable reason. Vendor text stays
        # out of reasons and logs; only the error type is logged.
        try:
            resend.Emails.send(
                {
                    "from": payload["from"],
                    "to": payload["to"],
                    "subject": payload["subject"],
                    "text": payload["text"],
                }
            )
        except Exception as exc:
            logger.warning("resend send failed: error=%s", type(exc).__name__)
            raise ResendError("resend-send-failed") from exc


class ResendEmailSender(EmailSender):
    """Prod sender. Key arrives once at composition time from server config."""

    def __init__(
        self, *, api_key: str, from_address: str, transport: EmailTransport | None = None
    ) -> None:
        self._api_key = api_key
        self._from_address = from_address
        self._transport = transport or ResendTransport(api_key)

    @classmethod
    def from_config(
        cls, *, api_key: str | None, from_address: str, transport: EmailTransport | None = None
    ) -> "ResendEmailSender":
        """Build from server config. Empty key yields a fail-closed sender."""
        return cls(api_key=api_key or "", from_address=from_address, transport=transport)

    def send(self, template: str, recipient: str, data: Mapping[str, Any]) -> SendResult:
        if not self._api_key:
            return SendResult(status=SendStatus.FAILED, reason="no-key")
        try:
            rendered = render(template, data)
        except TemplateValidationError as exc:
            return SendResult(status=SendStatus.FAILED, reason=str(exc))
        payload = {
            "from": self._from_address,
            "to": [recipient],
            "subject": rendered.subject,
            "text": rendered.body,
        }
        try:
            self._transport.post_email(payload)
        except ResendError as exc:
            # Log template plus cause only. Key and token stay out.
            logger.warning("resend send failed: template=%s reason=%s", template, exc)
            return SendResult(status=SendStatus.FAILED, reason=str(exc))
        return SendResult(status=SendStatus.SENT)
