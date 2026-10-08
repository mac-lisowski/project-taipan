"""Tokens service: mint, verify, burn over an open purpose value.

Purposes are plain strings, not a closed enum, so tomorrow's magic
links need no change here. Raw tokens exist only in the mint acts'
return values and in links; the store sees sha256 digests only. The
one-live-link rule lives here too: the pending pointer is a private
implementation detail no caller may touch.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from typing import Any

from api.kvstore import KVStore
from api.tokens.store import get_token_store

__all__ = [
    "PURPOSE_ACTIVATION",
    "PURPOSE_RESET",
    "TokenAlreadyUsed",
    "TokenData",
    "TokenError",
    "TokenNotFound",
    "TokenPurposeMismatch",
    "burn",
    "mint",
    "mint_single",
    "verify",
]

PURPOSE_ACTIVATION = "activation"
PURPOSE_RESET = "reset"

# Consumed records only need to answer "already used"; a short ttl lets
# the store reclaim them instead of lingering for the full original ttl.
CONSUMED_TTL_GRACE_SECONDS = 60

# The KV port has no scan, so the one-live-link rule keeps an explicit
# pointer per (purpose, user) in this keyspace; its value is a digest.
_PENDING_PREFIX = "pending:"


class TokenError(Exception):
    """Base for typed token failures."""


class TokenNotFound(TokenError):
    """Token is unknown, tampered, or expired."""


class TokenAlreadyUsed(TokenError):
    """Token was consumed by verify or burned."""


class TokenPurposeMismatch(TokenError):
    """Token's purpose differs from the one verify was asked for."""


@dataclass(frozen=True)
class TokenData:
    user_id: int
    purpose: str


def _digest(token: str) -> str:
    # Hashed at rest so a store leak shows digests, never usable links.
    return hashlib.sha256(token.encode()).hexdigest()


def _resolve_store(store: KVStore | None) -> KVStore:
    if store is not None:
        return store
    return get_token_store()


def _load(store: KVStore, token: str) -> tuple[str, dict[str, Any]]:
    raw = store.get(_digest(token))
    if raw is None:
        raise TokenNotFound("token is unknown or expired")
    try:
        record = json.loads(raw)
        return raw, {
            "user_id": int(record["user_id"]),
            "purpose": str(record["purpose"]),
            "ttl_seconds": int(record["ttl_seconds"]),
            "used": bool(record["used"]),
        }
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        raise TokenNotFound("token record is corrupt") from None


def mint(
    user_id: int,
    purpose: str,
    *,
    ttl_seconds: int,
    store: KVStore | None = None,
) -> str:
    """Create a single-use token for purpose; return the raw token once."""
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be positive")
    s = _resolve_store(store)
    token = secrets.token_urlsafe(32)
    record = json.dumps(
        {
            "user_id": user_id,
            "purpose": purpose,
            "ttl_seconds": ttl_seconds,
            "used": False,
        }
    )
    s.set(_digest(token), record, ttl_seconds=ttl_seconds)
    return token


def mint_single(
    user_id: int,
    purpose: str,
    *,
    ttl_seconds: int,
    store: KVStore | None = None,
) -> str:
    """Keep at most one live token per (user, purpose); return the live one.

    Older links for the same (user, purpose) never verify again once
    this returns, whatever the internal mint and kill order.
    """
    s = _resolve_store(store)
    raw = mint(user_id, purpose, ttl_seconds=ttl_seconds, store=s)
    pending_key = _PENDING_PREFIX + f"{purpose}:{user_id}"
    old_digest = s.get(pending_key)
    if old_digest is not None:
        s.delete(old_digest)
    s.set(pending_key, _digest(raw), ttl_seconds=ttl_seconds)
    return raw


def verify(
    token: str,
    purpose: str,
    store: KVStore | None = None,
) -> TokenData:
    """Consume the token if hash, purpose, expiry, and unused state pass."""
    s = _resolve_store(store)
    raw, record = _load(s, token)
    if record["purpose"] != purpose:
        raise TokenPurposeMismatch("token purpose does not match")
    if record["used"]:
        raise TokenAlreadyUsed("token was already used")
    record["used"] = True
    # The swap is atomic: a concurrent verify loses and reads as used.
    if not s.set_if_unchanged(
        _digest(token),
        raw,
        json.dumps(record),
        ttl_seconds=CONSUMED_TTL_GRACE_SECONDS,
    ):
        raise TokenAlreadyUsed("token was already used")
    return TokenData(user_id=record["user_id"], purpose=record["purpose"])


def burn(token: str, store: KVStore | None = None) -> None:
    """Mark the token used so later verify fails; unknown tokens are ignored."""
    s = _resolve_store(store)
    try:
        _, record = _load(s, token)
    except TokenNotFound:
        return
    record["used"] = True
    s.set(
        _digest(token),
        json.dumps(record),
        ttl_seconds=CONSUMED_TTL_GRACE_SECONDS,
    )
