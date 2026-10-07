"""The only path from a credential to a session token. Tokens out; no cookies here."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from api import sessions, users

if TYPE_CHECKING:
    from api.verifiers import CredentialVerifier

__all__ = ["InvalidCredentials", "issue", "login"]


class InvalidCredentials(Exception):
    """The verifier rejected the submitted credential."""


def issue(db: Session, user_id: int) -> str:
    """Mint a session token for user_id under the user's own tenant.

    A future reset flow must call sessions.revoke_all(user_id) before
    issue; the handshake itself never revokes.
    """
    tenant_id = users.tenant_id_for_user(db, user_id)
    return sessions.mint(user_id, tenant_id)


def login(db: Session, verifier: CredentialVerifier, email: str, password: str) -> str:
    """Verify the credential and issue a token, or raise InvalidCredentials."""
    user = verifier.verify(db, email, password)
    if user is None:
        raise InvalidCredentials()
    return issue(db, user.id)
