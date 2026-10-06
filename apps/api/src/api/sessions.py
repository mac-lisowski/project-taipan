"""Opaque login sessions: raw token in the cookie, sha256 in the DB."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from api.models import AuthSession

__all__ = ["mint", "resolve", "revoke"]

SESSION_DAYS = 7


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def mint(session: Session, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    session.add(
        AuthSession(
            token_sha256=_digest(token),
            user_id=user_id,
            expires_at=datetime.now(UTC) + timedelta(days=SESSION_DAYS),
        )
    )
    session.flush()
    return token


def revoke(session: Session, token: str) -> None:
    row = session.get(AuthSession, _digest(token))
    if row is not None:
        session.delete(row)
        session.flush()


def resolve(session: Session, token: str) -> AuthSession | None:
    row = session.get(AuthSession, _digest(token))
    if row is None or row.expires_at <= datetime.now(UTC):
        return None
    return row
