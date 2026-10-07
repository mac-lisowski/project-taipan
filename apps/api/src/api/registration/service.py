"""Registration acts: request reads the switch, activate never does, so mailed links outlive a close."""

from __future__ import annotations

import logging

from email_delivery import EmailSender
from email_delivery.templates import ACTIVATION, rendered_send
from sqlalchemy.orm import Session

from api import auth_flow, system_settings, tokens, users
from api.config import get_config
from api.credentials import WeakPassword

__all__ = ["APP_NAME", "RegistrationClosed", "WeakPassword", "activate", "request"]

logger = logging.getLogger(__name__)

APP_NAME = "Taipan"


class RegistrationClosed(Exception):
    """Sign up is switched off; the caller maps this to 404."""


def request(session: Session, *, email: str, sender: EmailSender, app_base_url: str) -> None:
    """Answer the same for every email; only a passwordless account gets mail."""
    if not system_settings.get_registration_enabled(session):
        raise RegistrationClosed()
    user = users.get_by_email(session, email)
    if user is not None and user.hashed_password is not None:
        return
    if user is None:
        user = users.register_passwordless(session, email)
    raw = tokens.mint_single(
        user.id,
        tokens.PURPOSE_ACTIVATION,
        ttl_seconds=get_config().store.activation_token_ttl_seconds,
    )
    link = f"{app_base_url}/register?token={raw}"
    try:
        rendered_send(sender, ACTIVATION, user.email, {"app_name": APP_NAME, "link": link})
    except Exception:  # noqa: BLE001 - mail must never break the neutral reply
        logger.warning("activation mail failed to send")


def activate(session: Session, *, token: str, new_password: str) -> str:
    """Set the password from the link and log the user in at once."""
    user = auth_flow.set_password_with_token(
        session,
        token=token,
        purpose=tokens.PURPOSE_ACTIVATION,
        password=new_password,
        revoke_sessions=False,
    )
    return auth_flow.issue(session, user.id)
