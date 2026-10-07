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
    "revoke_all",
    "set_session_cookie",
    "tenant_id_for_token",
]

COOKIE_NAME = "session"

# The epoch must outlive every session it guards; no session ttl reaches it.
EPOCH_TTL_SECONDS = 10 * 365 * 24 * 3600


@dataclass(frozen=True)
class SessionData:
    user_id: int
    tenant_id: str


def _store(store: SessionStore | None) -> SessionStore:
    return store if store is not None else get_session_store()


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _epoch_key(user_id: int) -> str:
    # Contains '-', so it never collides with hex-digest session keys.
    return f"session-epoch:{user_id}"


def _current_epoch(store: SessionStore, user_id: int) -> str | None:
    # No refresh from mints: the fixed TTL outlives any session ttl, so a
    # short mint can never shorten it under a live long session.
    return store.get(_epoch_key(user_id))


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
    digest = _digest(token)
    epoch = _current_epoch(s, user_id)
    payload = json.dumps({"user_id": user_id, "tenant_id": tenant_id, "epoch": epoch})
    s.set(digest, payload, ttl_seconds=ttl)
    return token


def resolve(token: str, store: SessionStore | None = None) -> SessionData | None:
    """Retrieve SessionData for token; return None if token is invalid or expired."""
    s = _store(store)
    raw = s.get(_digest(token))
    if raw is None:
        return None
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        user_id = int(data["user_id"])
        tenant_id = str(data["tenant_id"])
        # Legacy records carry no epoch; None matches only a missing key.
        epoch = data.get("epoch")
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None
    # A mismatch kills revoked sessions, even ones the epoch never saw.
    if epoch != s.get(_epoch_key(user_id)):
        return None
    return SessionData(user_id=user_id, tenant_id=tenant_id)


def revoke(token: str, store: SessionStore | None = None) -> None:
    """Revoke session token from store."""
    _store(store).delete(_digest(token))


def revoke_all(user_id: int, store: SessionStore | None = None) -> None:
    """Revoke every live session for user_id, indexed or not.

    One blind epoch write: there is no read-modify-write to lose a mint
    through, a mint that read the old epoch dies on the mismatch, and
    the first revoke also kills sessions minted before epoch tracking.
    """
    _store(store).set(
        _epoch_key(user_id),
        secrets.token_hex(8),
        ttl_seconds=EPOCH_TTL_SECONDS,
    )


def tenant_id_for_token(token: str, store: SessionStore | None = None) -> str | None:
    """Return tenant_id for session token without opening database session."""
    sess = resolve(token, store)
    return sess.tenant_id if sess is not None else None
