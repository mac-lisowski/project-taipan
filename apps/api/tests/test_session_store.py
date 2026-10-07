"""Tests for session store port and adapters."""

import pytest
from api.config import Config
from api.session_store import (
    MemorySessionStore,
    RedisSessionStore,
    SessionStore,
    build_session_store,
    get_session_store,
    set_session_store,
)
from api_testsupport import FakeClock, FakeRedis


def test_memory_session_store_crud() -> None:
    store = MemorySessionStore()
    assert store.get("token-1") is None

    store.set("token-1", "user-123", ttl_seconds=60)
    assert store.get("token-1") == "user-123"

    store.delete("token-1")
    assert store.get("token-1") is None

    # deleting missing key is a safe no-op
    store.delete("token-1")


def test_memory_session_store_ttl_expiry() -> None:
    clock = FakeClock()
    store = MemorySessionStore(clock=clock)
    store.set("token-1", "payload", ttl_seconds=10)

    clock.advance(9.9)
    assert store.get("token-1") == "payload"

    clock.advance(0.2)
    assert store.get("token-1") is None


def test_memory_session_store_rejects_non_positive_ttl() -> None:
    store = MemorySessionStore()
    with pytest.raises(ValueError, match="ttl_seconds must be positive"):
        store.set("token", "val", ttl_seconds=0)

    with pytest.raises(ValueError, match="ttl_seconds must be positive"):
        store.set("token", "val", ttl_seconds=-10)


def test_memory_session_store_clear() -> None:
    store = MemorySessionStore()
    store.set("k1", "v1", ttl_seconds=60)
    store.set("k2", "v2", ttl_seconds=60)
    store.clear()
    assert store.get("k1") is None
    assert store.get("k2") is None


def test_memory_set_if_unchanged_writes_when_current_matches() -> None:
    store = MemorySessionStore()
    store.set("t1", "old", ttl_seconds=60)

    assert store.set_if_unchanged("t1", "old", "new", ttl_seconds=60) is True
    assert store.get("t1") == "new"


def test_memory_set_if_unchanged_loses_when_current_differs() -> None:
    store = MemorySessionStore()
    store.set("t1", "current", ttl_seconds=60)

    assert store.set_if_unchanged("t1", "stale", "new", ttl_seconds=60) is False
    # The loser must not write; the current value survives untouched.
    assert store.get("t1") == "current"


def test_memory_set_if_unchanged_rejects_non_positive_ttl() -> None:
    store = MemorySessionStore()

    with pytest.raises(ValueError, match="ttl_seconds must be positive"):
        store.set_if_unchanged("t1", "old", "new", ttl_seconds=0)


def test_redis_session_store_crud() -> None:
    clock = FakeClock()
    fake_redis = FakeRedis(clock)
    store = RedisSessionStore(fake_redis, prefix="sess:")

    assert isinstance(store, SessionStore)
    assert store.get("t1") is None

    store.set("t1", "user-456", ttl_seconds=30)
    assert store.get("t1") == "user-456"
    assert "sess:t1" in fake_redis.data

    clock.advance(29)
    assert store.get("t1") == "user-456"

    clock.advance(2)
    assert store.get("t1") is None


def test_redis_session_store_decodes_bytes() -> None:
    clock = FakeClock()
    fake_redis = FakeRedis(clock)
    fake_redis.data["session:t2"] = (b"bytes-value", None)

    store = RedisSessionStore(fake_redis)
    assert store.get("t2") == "bytes-value"


def test_redis_session_store_delete() -> None:
    clock = FakeClock()
    fake_redis = FakeRedis(clock)
    store = RedisSessionStore(fake_redis)

    store.set("t3", "val", ttl_seconds=60)
    assert store.get("t3") == "val"

    store.delete("t3")
    assert store.get("t3") is None
    assert "session:t3" not in fake_redis.data


def test_redis_session_store_rejects_non_positive_ttl() -> None:
    clock = FakeClock()
    fake_redis = FakeRedis(clock)
    store = RedisSessionStore(fake_redis)

    with pytest.raises(ValueError, match="ttl_seconds must be positive"):
        store.set("token", "val", ttl_seconds=0)


def test_redis_set_if_unchanged_writes_when_current_matches() -> None:
    clock = FakeClock()
    fake_redis = FakeRedis(clock)
    store = RedisSessionStore(fake_redis, prefix="sess:")
    store.set("t1", "old", ttl_seconds=60)

    assert store.set_if_unchanged("t1", "old", "new", ttl_seconds=30) is True
    assert store.get("t1") == "new"

    # The win must carry the new ttl, like the script's EX argument.
    clock.advance(30)
    assert store.get("t1") is None


def test_redis_set_if_unchanged_loses_when_current_differs() -> None:
    clock = FakeClock()
    fake_redis = FakeRedis(clock)
    store = RedisSessionStore(fake_redis, prefix="sess:")
    fake_redis.set("sess:t1", "current", ex=60)

    assert store.set_if_unchanged("t1", "stale", "new", ttl_seconds=30) is False
    # The loser must not write; the current value survives untouched.
    assert store.get("t1") == "current"


def test_redis_set_if_unchanged_rejects_non_positive_ttl() -> None:
    fake_redis = FakeRedis(FakeClock())
    store = RedisSessionStore(fake_redis)

    with pytest.raises(ValueError, match="ttl_seconds must be positive"):
        store.set_if_unchanged("t1", "old", "new", ttl_seconds=0)


def test_build_session_store_wires_redis_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = Config.from_env({"API_REDIS_URL": "redis://localhost:6379/9"})
    captured_urls: list[str] = []

    class DummyRedis:
        @classmethod
        def from_url(cls, url: str) -> "DummyRedis":
            captured_urls.append(url)
            return cls()

    monkeypatch.setattr("api.session_store.Redis", DummyRedis)
    store = build_session_store(cfg)
    assert isinstance(store, RedisSessionStore)
    assert captured_urls == ["redis://localhost:6379/9"]


def test_get_and_set_session_store() -> None:
    custom_store = MemorySessionStore()
    set_session_store(custom_store)
    try:
        assert get_session_store() is custom_store
    finally:
        set_session_store(None)
