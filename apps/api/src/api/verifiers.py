"""Credential verifier slot for session issue. Password is the first verifier."""

from __future__ import annotations

from typing import Protocol

from sqlalchemy.orm import Session

from api import users
from api.credentials import InactiveUser
from api.models import User

__all__ = ["CredentialVerifier", "PasswordVerifier", "get_credential_verifier"]


class CredentialVerifier(Protocol):
    """Checks a submitted credential and returns the user, or None."""

    def verify(self, db: Session, email: str, password: str) -> User | None: ...


class PasswordVerifier:
    """First verifier: email plus password through the users authority."""

    def verify(self, db: Session, email: str, password: str) -> User | None:
        # An inactive user failed the credential check; the router maps
        # None to 401, so activation state never leaks into the response.
        try:
            return users.authenticate(db, email, password)
        except InactiveUser:
            return None


def get_credential_verifier() -> CredentialVerifier:
    return PasswordVerifier()
