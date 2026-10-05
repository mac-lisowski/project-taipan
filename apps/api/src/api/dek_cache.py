"""DekCache adapters: process-local L1, Redis L2, both degrade on error."""

import logging
import threading
import time
from collections.abc import Callable

from redis import Redis, RedisError

_log = logging.getLogger(__name__)

# Public so tests assert key shape through the adapter, never a literal.
KEY_PREFIX = "crypto:dek:"


class LocalTtlDekCache:
    """Process-local first tier. A short TTL bounds rotation staleness."""

    def __init__(self, ttl_seconds: int, monotonic: Callable[[], float] = time.monotonic) -> None:
        self._ttl = ttl_seconds
        self._monotonic = monotonic
        self._entries: dict[str, tuple[bytes, float]] = {}
        self._lock = threading.Lock()

    def get(self, tenant_id: str) -> bytes | None:
        with self._lock:
            entry = self._entries.get(tenant_id)
            if entry is None:
                return None
            dek, expire_at = entry
            if self._monotonic() >= expire_at:
                del self._entries[tenant_id]
                return None
            return dek

    def put(self, tenant_id: str, dek: bytes, ttl_seconds: int) -> None:
        # A caller TTL under the floor wins: never outlive the remote tier.
        ttl = min(self._ttl, ttl_seconds) if ttl_seconds > 0 else self._ttl
        with self._lock:
            self._entries[tenant_id] = (dek, self._monotonic() + ttl)


class RedisDekCache:
    """Implements the crypto DekCache port. Errors log and read as a miss."""

    def __init__(self, client: Redis, ttl_seconds: int) -> None:
        self._client = client
        self._ttl_seconds = ttl_seconds

    def get(self, tenant_id: str) -> bytes | None:
        try:
            return self._client.get(KEY_PREFIX + tenant_id)
        except RedisError:
            # Logs never carry key material; the tenant id stays out too.
            _log.warning("dek cache read failed; continuing without the cache")
            return None

    def put(self, tenant_id: str, dek: bytes, ttl_seconds: int) -> None:
        # The caller may defer the choice; the configured default applies then.
        ttl = ttl_seconds if ttl_seconds > 0 else self._ttl_seconds
        try:
            self._client.set(KEY_PREFIX + tenant_id, dek, ex=ttl)
        except RedisError:
            _log.warning("dek cache write failed; continuing without the cache")


class TwoTierDekCache:
    """DekCache port over a local L1 and a Redis L2.

    Without the L1 every field operation pays one Redis round trip,
    which scales with rows x columns on every query.
    """

    def __init__(self, local: LocalTtlDekCache, remote: RedisDekCache) -> None:
        self._local = local
        self._remote = remote

    @property
    def local(self) -> LocalTtlDekCache:
        return self._local

    @property
    def remote(self) -> RedisDekCache:
        return self._remote

    def get(self, tenant_id: str) -> bytes | None:
        hit = self._local.get(tenant_id)
        if hit is not None:
            return hit
        dek = self._remote.get(tenant_id)
        if dek is not None:
            self._local.put(tenant_id, dek, ttl_seconds=0)
        return dek

    def put(self, tenant_id: str, dek: bytes, ttl_seconds: int) -> None:
        self._local.put(tenant_id, dek, ttl_seconds)
        self._remote.put(tenant_id, dek, ttl_seconds)
