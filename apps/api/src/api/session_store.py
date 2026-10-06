"""Session store port and adapters.

Provides a key-value interface with TTL for session storage.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Protocol, runtime_checkable

from redis import Redis

from api.config import Config, get_config


@runtime_checkable
class SessionStore(Protocol):
    """Port for session storage: get, set with TTL, and delete."""

    def get(self, key: str) -> str | None:
        """Retrieve value by key. Return None if absent or expired."""
        ...

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        """Store value with positive time-to-live in seconds."""
        ...

    def delete(self, key: str) -> None:
        """Remove value by key."""
        ...


class MemorySessionStore:
    """In-memory session store adapter for tests and local seams."""

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self._clock = clock if clock is not None else time.monotonic
        self._entries: dict[str, tuple[str, float]] = {}

    def get(self, key: str) -> str | None:
        item = self._entries.get(key)
        if item is None:
            return None
        value, expires_at = item
        if self._clock() >= expires_at:
            del self._entries[key]
            return None
        return value

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self._entries[key] = (value, self._clock() + ttl_seconds)

    def delete(self, key: str) -> None:
        self._entries.pop(key, None)

    def clear(self) -> None:
        self._entries.clear()


class RedisSessionStore:
    """Redis session store adapter for production."""

    def __init__(self, client: Redis, prefix: str = "session:") -> None:
        self._client = client
        self._prefix = prefix

    def _prefixed(self, key: str) -> str:
        return f"{self._prefix}{key}"

    def get(self, key: str) -> str | None:
        raw = self._client.get(self._prefixed(key))
        if raw is None:
            return None
        if isinstance(raw, bytes):
            return raw.decode("utf-8")
        return str(raw)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self._client.set(self._prefixed(key), value, ex=ttl_seconds)

    def delete(self, key: str) -> None:
        self._client.delete(self._prefixed(key))


_session_store: SessionStore | None = None


def get_session_store() -> SessionStore:
    """Return active session store, initializing default Redis adapter if unset."""
    global _session_store
    if _session_store is None:
        _session_store = build_session_store()
    return _session_store


def set_session_store(store: SessionStore | None) -> None:
    """Set active session store for testing or lifecycle wiring."""
    global _session_store
    _session_store = store


def build_session_store(config: Config | None = None) -> SessionStore:
    """Build production Redis session store from configuration."""
    cfg = config or get_config()
    client = Redis.from_url(cfg.redis_url)
    return RedisSessionStore(client)
