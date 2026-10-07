"""Password reset rules: request a link, consume it, rotate the password.

Usable without FastAPI. Unlike password_change, the reset act composes
revoke_all plus session issue itself: the spec pins the whole reset
contract (burn, rotate, revoke, log in) inside one service call.
"""

from __future__ import annotations

import logging

from email_delivery import EmailSender
from email_delivery.templates import RESET, rendered_send
from sqlalchemy.orm import Session

from api import auth_flow, sessions, tokens, users
from api.config import get_config
from api.credentials import WeakPassword, ensure_acceptable, hash_password

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
    """Burn the token, swap the hash, kill every session, log the user in.

    Strength runs before verify: verify burns atomically, and a weak
    password must leave the token live for a corrected retry.
    """
    ensure_acceptable(new_password)
    data = tokens.verify(token, tokens.PURPOSE_RESET)
    user = users.get(session, data.user_id)
    if not user.is_active:
        # Neutral rejection: same error family, no hash write, no login.
        raise tokens.TokenError("user is not active")
    user.hashed_password = hash_password(new_password)
    session.flush()
    sessions.revoke_all(user.id)
    return auth_flow.issue(session, user.id)
