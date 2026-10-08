"""The only path from a credential to a session. Tokens out; no cookies here.

The token-to-password core lives here too: activation and reset are
the same act up to one deactivation and revocation policy, so the
order (strength, burn, gate, hash, revoke) is written once.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from api import sessions, tokens, users
from api.credentials import ensure_acceptable, hash_password

if TYPE_CHECKING:
    from api.models import User
    from api.verifiers import CredentialVerifier

__all__ = ["InvalidCredentials", "issue", "login", "set_password_with_token"]


class InvalidCredentials(Exception):
    """The verifier rejected the submitted credential."""


def issue(db: Session, user_id: int) -> str:
    """Mint a session token for user_id under the user's own tenant.

    Callers that must kill live sessions (reset) revoke before issue;
    the handshake itself never revokes.
    """
    tenant_id = users.tenant_id_for_user(db, user_id)
    return sessions.mint(user_id, tenant_id)


def login(db: Session, verifier: CredentialVerifier, email: str, password: str) -> str:
    """Verify the credential and issue a token, or raise InvalidCredentials."""
    user = verifier.verify(db, email, password)
    if user is None:
        raise InvalidCredentials()
    return issue(db, user.id)


def set_password_with_token(
    db: Session,
    *,
    token: str,
    purpose: str,
    password: str,
    revoke_sessions: bool,
) -> User:
    """Consume the token, set the password, apply the caller's policy.

    Strength runs before verify: verify burns atomically, and a weak
    password must leave the token live for a corrected retry. An
    inactive user raises the same token error as a dead link, so the
    client contract stays one string. Session mint stays with the
    caller; this act only revokes when the policy says so.
    """
    ensure_acceptable(password)
    data = tokens.verify(token, purpose)
    user = users.get(db, data.user_id)
    if not user.is_active:
        # Neutral rejection: no hash write, same error family as a dead link.
        raise tokens.TokenError("user is not active")
    user.hashed_password = hash_password(password)
    db.flush()
    if revoke_sessions:
        sessions.revoke_all(user.id)
    return user
