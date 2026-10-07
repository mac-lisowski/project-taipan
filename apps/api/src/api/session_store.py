"""Session store port and adapters.

Provides a key-value interface with TTL for session storage.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Protocol, runtime_checkable

from redis import Redis

from api.config import Config, get_config

# Swap only when the stored value is still the one we read; the compare
# and the write must be one indivisible step for single-use guarantees.
_CAS_LUA = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    redis.call('set', KEYS[1], ARGV[2], 'EX', ARGV[3])
    return 1
end
return 0
"""


@runtime_checkable
class SessionStore(Protocol):
    """Port for session storage: get, set with TTL, delete, and atomic swap."""

    def get(self, key: str) -> str | None:
        """Retrieve value by key. Return None if absent or expired."""
        ...

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        """Store value with positive time-to-live in seconds."""
        ...

    def set_if_unchanged(self, key: str, expected: str, value: str, ttl_seconds: int) -> bool:
        """Atomically store value only if current value equals expected.

        Returns False without writing when another writer changed the key.
        """
        ...

    def delete(self, key: str) -> None:
        """Remove value by key."""
        ...


class MemorySessionStore:
    """In-memory session store adapter for tests and local seams."""

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self._clock = clock if clock is not None else time.monotonic
        self._entries: dict[str, tuple[str, float]] = {}
        # One lock so a concurrent set_if_unchanged cannot interleave.
        self._lock = threading.Lock()

    def get(self, key: str) -> str | None:
        with self._lock:
            return self._get(key)

    def _get(self, key: str) -> str | None:
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
        with self._lock:
            self._entries[key] = (value, self._clock() + ttl_seconds)

    def set_if_unchanged(self, key: str, expected: str, value: str, ttl_seconds: int) -> bool:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        with self._lock:
            if self._get(key) != expected:
                return False
            self._entries[key] = (value, self._clock() + ttl_seconds)
            return True

    def delete(self, key: str) -> None:
        with self._lock:
            self._entries.pop(key, None)

    def clear(self) -> None:
        with self._lock:
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

    def set_if_unchanged(self, key: str, expected: str, value: str, ttl_seconds: int) -> bool:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        result = self._client.eval(_CAS_LUA, 1, self._prefixed(key), expected, value, ttl_seconds)
        return int(result) == 1

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
