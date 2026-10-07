"""Token store port and adapters.

Records are keyed by token hash; the value carries purpose and used
state. Expiry is the store's TTL job, so verify stays one lookup. The
atomic swap keeps single use true under concurrent verifies.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from redis import Redis

from api.config import get_config
from api.session_store import MemorySessionStore, RedisSessionStore


@runtime_checkable
class TokenStore(Protocol):
    """Port for token records: get, set with TTL, and atomic swap, keyed by hash."""

    def get(self, key: str) -> str | None:
        """Return the record for key, or None when absent or expired."""
        ...

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        """Store record with positive time-to-live in seconds."""
        ...

    def set_if_unchanged(self, key: str, expected: str, value: str, ttl_seconds: int) -> bool:
        """Atomically store value only if current value equals expected."""
        ...


class MemoryTokenStore(MemorySessionStore):
    """In-memory token store adapter for tests and local seams."""


_token_store: TokenStore | None = None


def _build_token_store() -> RedisSessionStore:
    client = Redis.from_url(get_config().redis_url)
    # Own prefix keeps token digests out of the session key namespace.
    return RedisSessionStore(client, prefix="token:")


def get_token_store() -> TokenStore:
    """Return the shared token store, initializing the Redis adapter if unset."""
    global _token_store
    if _token_store is None:
        _token_store = _build_token_store()
    return _token_store


def set_token_store(store: TokenStore | None) -> None:
    """Set the shared token store for testing or lifecycle wiring."""
    global _token_store
    _token_store = store
