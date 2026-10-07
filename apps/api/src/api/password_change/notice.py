"""Best-effort change notice through the shared email seam."""

import logging

from email_delivery import EmailSender
from email_delivery.templates import PASSWORD_CHANGE, rendered_send

logger = logging.getLogger(__name__)

APP_NAME = "Taipan"


def send_change_notice(sender: EmailSender, recipient: str) -> None:
    """Send once; a failure only logs and never blocks the change."""
    try:
        rendered_send(sender, PASSWORD_CHANGE, recipient, {"app_name": APP_NAME})
    except Exception:  # noqa: BLE001 - mail must never block the change
        logger.warning("password change notice failed to send")
