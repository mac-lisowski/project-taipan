"""Password reset rules: request a link, consume it, rotate the password.

Usable without FastAPI. The reset act delegates the token-to-password
core to auth_flow and keeps the whole reset contract (burn, rotate,
revoke, log in) inside one service call.
"""

from __future__ import annotations

import logging

from email_delivery import EmailSender
from email_delivery.templates import RESET, rendered_send
from sqlalchemy.orm import Session

from api import auth_flow, tokens, users
from api.config import get_config
from api.credentials import WeakPassword

__all__ = ["APP_NAME", "WeakPassword", "request", "reset"]

logger = logging.getLogger(__name__)

APP_NAME = "Taipan"


def request(session: Session, *, email: str, sender: EmailSender, app_base_url: str) -> None:
    """Look up the email in silence; a known active user gets one link."""
    user = users.get_by_email(session, email)
    if user is None or not user.is_active:
        return
    raw = tokens.mint(
        user.id,
        tokens.PURPOSE_RESET,
        ttl_seconds=get_config().store.reset_token_ttl_seconds,
    )
    link = f"{app_base_url}/reset?token={raw}"
    try:
        rendered_send(sender, RESET, user.email, {"app_name": APP_NAME, "link": link})
    except Exception:  # noqa: BLE001 - mail must never break the neutral reply
        logger.warning("password reset mail failed to send")


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
