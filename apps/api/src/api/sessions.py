"""Opaque login sessions: stored in SessionStore with TTL."""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from typing import TYPE_CHECKING

from api.config import get_config
from api.session_store import SessionStore, get_session_store

if TYPE_CHECKING:
    from fastapi import Response

__all__ = [
    "COOKIE_NAME",
    "SessionData",
    "clear_session_cookie",
    "mint",
    "resolve",
    "revoke",
    "set_session_cookie",
    "tenant_id_for_token",
]

COOKIE_NAME = "session"


@dataclass(frozen=True)
class SessionData:
    user_id: int
    tenant_id: str


def _store(store: SessionStore | None) -> SessionStore:
    return store if store is not None else get_session_store()


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def set_session_cookie(response: Response, token: str) -> None:
    """Set HttpOnly session cookie on response."""
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", path="/")


def clear_session_cookie(response: Response) -> None:
    """Clear session cookie on response."""
    response.delete_cookie(COOKIE_NAME, path="/")


def mint(
    user_id: int,
    tenant_id: str,
    store: SessionStore | None = None,
    ttl_seconds: int | None = None,
) -> str:
    """Mint new session token and store user_id and tenant_id with TTL."""
    s = _store(store)
    ttl = ttl_seconds if ttl_seconds is not None else get_config().session_ttl_seconds
    token = secrets.token_urlsafe(32)
    payload = json.dumps({"user_id": user_id, "tenant_id": tenant_id})
    s.set(_digest(token), payload, ttl_seconds=ttl)
    return token


def resolve(token: str, store: SessionStore | None = None) -> SessionData | None:
    """Retrieve SessionData for token; return None if token is invalid or expired."""
    s = _store(store)
    raw = s.get(_digest(token))
    if raw is None:
        return None
    try:
        data = json.loads(raw)
        return SessionData(user_id=int(data["user_id"]), tenant_id=str(data["tenant_id"]))
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


def revoke(token: str, store: SessionStore | None = None) -> None:
    """Revoke session token from store."""
    _store(store).delete(_digest(token))


def tenant_id_for_token(token: str, store: SessionStore | None = None) -> str | None:
    """Return tenant_id for session token without opening database session."""
    sess = resolve(token, store)
    return sess.tenant_id if sess is not None else None
