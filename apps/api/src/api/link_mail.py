"""Link mail: one home for app name, link build, and best effort send."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from urllib.parse import urlencode

from email_delivery import EmailSender
from email_delivery.templates import rendered_send

from api.config import get_config
from api.mail import APP_NAME

__all__ = ["MailLink", "build_link", "send_link", "send_notice"]

logger = logging.getLogger(__name__)

# On-call reads one pattern for every swallowed mail.
_FAILURE = "mail send failed template=%s recipient=%s error=%s"


@dataclass(frozen=True)
class MailLink:
    """Typed link: a path under the app origin plus its query parts."""

    path: str
    query: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Copy then wrap: a caller-held dict must not reach the stored query.
        object.__setattr__(self, "query", MappingProxyType(dict(self.query)))


def build_link(link: MailLink) -> str:
    """Absolute URL from the configured origin; passes render validation."""
    base = get_config().mail.app_base_url.rstrip("/")
    url = f"{base}{link.path}"
    if link.query:
        url = f"{url}?{urlencode(link.query)}"
    return url


def send_link(sender: EmailSender, template: str, recipient: str, link: MailLink) -> None:
    """Render and send link mail; a failure never escapes to the caller."""
    data = {"app_name": APP_NAME, "link": build_link(link)}
    _send_best_effort(sender, template, recipient, data)


def send_notice(sender: EmailSender, template: str, recipient: str) -> None:
    """Render and send link-free notice mail; a failure never escapes."""
    _send_best_effort(sender, template, recipient, {"app_name": APP_NAME})


def _send_best_effort(
    sender: EmailSender,
    template: str,
    recipient: str,
    data: Mapping[str, str],
) -> None:
    try:
        rendered_send(sender, template, recipient, data)
    except Exception as exc:  # noqa: BLE001 - mail must never break the caller's answer
        logger.warning(_FAILURE, template, recipient, exc)
