"""Best-effort change notice through the shared email seam."""

from email_delivery import EmailSender
from email_delivery.templates import PASSWORD_CHANGE

from api.link_mail import send_notice


def send_change_notice(sender: EmailSender, recipient: str) -> None:
    """Send once; a failure only logs and never blocks the change."""
    send_notice(sender, PASSWORD_CHANGE, recipient)
