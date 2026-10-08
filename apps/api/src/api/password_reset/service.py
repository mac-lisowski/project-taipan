"""Password reset rules: request a link, consume it, rotate the password.

Usable without FastAPI. The reset act delegates the token-to-password
core to auth_flow and keeps the whole reset contract (burn, rotate,
revoke, log in) inside one service call.
"""

from __future__ import annotations

from email_delivery import EmailSender
from email_delivery.templates import RESET
from sqlalchemy.orm import Session

from api import auth_flow, tokens, users
from api.config import get_config
from api.credentials import WeakPassword
from api.link_mail import MailLink, send_link

__all__ = ["WeakPassword", "request", "reset"]


def request(session: Session, *, email: str, sender: EmailSender) -> None:
    """Look up the email in silence; a known active user gets one link."""
    user = users.get_by_email(session, email)
    if user is None or not user.is_active:
        return
    raw = tokens.mint(
        user.id,
        tokens.PURPOSE_RESET,
        ttl_seconds=get_config().store.reset_token_ttl_seconds,
    )
    send_link(sender, RESET, user.email, MailLink("/reset", {"token": raw}))


def reset(session: Session, *, token: str, new_password: str) -> str:
    """Burn the token, swap the hash, kill every session, log the user in."""
    user = auth_flow.set_password_with_token(
        session,
        token=token,
        purpose=tokens.PURPOSE_RESET,
        password=new_password,
        revoke_sessions=True,
    )
    return auth_flow.issue(session, user.id)
