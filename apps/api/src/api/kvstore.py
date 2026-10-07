"""Namespaced key-value store port and adapters.

One KV port with TTL and atomic swap. Both adapters take a required
namespace and prefix keys the same way, so keyspaces coexist on one
Redis client and one conformance suite proves both adapters.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Protocol

from redis import Redis

from api.config import Config, get_config

SESSION_KEYS = "session:"
TOKEN_KEYS = "token:"

# Swap only when the stored value is still the one we read; the compare
# and the write must be one indivisible step for single-use guarantees.
_CAS_LUA = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    redis.call('set', KEYS[1], ARGV[2], 'EX', ARGV[3])
    return 1
end
return 0
"""


def _require_positive_ttl(ttl_seconds: int) -> None:
    """Reject non-positive ttl so no adapter can store an already-expired value."""
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be positive")


class KVStore(Protocol):
    """Port for keyed storage: get, set with TTL, delete, and atomic swap."""

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


class MemoryKVStore:
    """In-memory KV store adapter for tests and local seams."""

    def __init__(
        self,
        namespace: str,
        clock: Callable[[], float] | None = None,
        entries: dict[str, tuple[str, float]] | None = None,
    ) -> None:
        self._namespace = namespace
        self._clock = clock if clock is not None else time.monotonic
        # Public seam: tests observe and share the backing dict, like FakeRedis.data.
        self.entries: dict[str, tuple[str, float]] = entries if entries is not None else {}
        # One lock so a concurrent set_if_unchanged cannot interleave.
        self._lock = threading.Lock()

    def _prefixed(self, key: str) -> str:
        return f"{self._namespace}{key}"

    def get(self, key: str) -> str | None:
        with self._lock:
            return self._get(self._prefixed(key))

    def _get(self, prefixed: str) -> str | None:
        item = self.entries.get(prefixed)
        if item is None:
            return None
        value, expires_at = item
        if self._clock() >= expires_at:
            del self.entries[prefixed]
            return None
        return value

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        _require_positive_ttl(ttl_seconds)
        with self._lock:
            self.entries[self._prefixed(key)] = (value, self._clock() + ttl_seconds)

    def set_if_unchanged(self, key: str, expected: str, value: str, ttl_seconds: int) -> bool:
        _require_positive_ttl(ttl_seconds)
        with self._lock:
            if self._get(self._prefixed(key)) != expected:
                return False
            self.entries[self._prefixed(key)] = (value, self._clock() + ttl_seconds)
            return True

    def delete(self, key: str) -> None:
        with self._lock:
            self.entries.pop(self._prefixed(key), None)


class RedisKVStore:
    """Redis KV store adapter for production."""

    def __init__(self, client: Redis, namespace: str) -> None:
        self._client = client
        self._namespace = namespace

    def _prefixed(self, key: str) -> str:
        return f"{self._namespace}{key}"

    def get(self, key: str) -> str | None:
        raw = self._client.get(self._prefixed(key))
        if raw is None:
            return None
        if isinstance(raw, bytes):
            return raw.decode("utf-8")
        return str(raw)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        _require_positive_ttl(ttl_seconds)
        self._client.set(self._prefixed(key), value, ex=ttl_seconds)

    def set_if_unchanged(self, key: str, expected: str, value: str, ttl_seconds: int) -> bool:
        _require_positive_ttl(ttl_seconds)
        result = self._client.eval(_CAS_LUA, 1, self._prefixed(key), expected, value, ttl_seconds)
        return int(result) == 1

    def delete(self, key: str) -> None:
        self._client.delete(self._prefixed(key))


_session_store: KVStore | None = None


def get_session_store() -> KVStore:
    """Return active session store, initializing default Redis adapter if unset."""
    global _session_store
    if _session_store is None:
        _session_store = build_session_store()
    return _session_store


def set_session_store(store: KVStore | None) -> None:
    """Set active session store for testing or lifecycle wiring."""
    global _session_store
    _session_store = store


def build_session_store(config: Config | None = None) -> KVStore:
    """Build production Redis session store from configuration."""
    cfg = config or get_config()
    client = Redis.from_url(cfg.store.redis_url)
    return RedisKVStore(client, namespace=SESSION_KEYS)
