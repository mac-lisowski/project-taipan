"""Tests for the namespaced KV store port and adapters."""

import pytest
from api.config import Config
from api.kvstore import (
    SESSION_KEYS,
    TOKEN_KEYS,
    KVStore,
    MemoryKVStore,
    RedisKVStore,
    build_session_store,
    get_session_store,
    set_session_store,
)
from api.tokens.store import build_token_store
from api_testsupport import FakeClock, FakeRedis

IMPLS = ["memory", "redis"]
# Real session keys are sha256 hex digests; the shape must not collide
# with the epoch key family.
DIGEST = "aa" * 32
EPOCH = "session-epoch:7"


def make_store(impl: str, clock: FakeClock) -> KVStore:
    """Build one conformance store on the session namespace."""
    if impl == "memory":
        return MemoryKVStore(SESSION_KEYS, clock=clock)
    return RedisKVStore(FakeRedis(clock), namespace=SESSION_KEYS)


@pytest.mark.parametrize("impl", IMPLS)
def test_crud_round_trip(impl: str) -> None:
    store = make_store(impl, FakeClock())

    assert store.get(DIGEST) is None
    store.set(DIGEST, "user-1", ttl_seconds=60)
    assert store.get(DIGEST) == "user-1"
    store.delete(DIGEST)
    assert store.get(DIGEST) is None


@pytest.mark.parametrize("impl", IMPLS)
def test_delete_missing_key_is_safe_noop(impl: str) -> None:
    store = make_store(impl, FakeClock())

    store.delete(DIGEST)
    assert store.get(DIGEST) is None


@pytest.mark.parametrize("impl", IMPLS)
def test_ttl_expiry_reads_before_and_gone_after(impl: str) -> None:
    clock = FakeClock()
    store = make_store(impl, clock)

    store.set(DIGEST, "payload", ttl_seconds=10)
    clock.advance(9.9)
    assert store.get(DIGEST) == "payload"

    clock.advance(0.2)
    assert store.get(DIGEST) is None


@pytest.mark.parametrize("impl", IMPLS)
def test_non_positive_ttl_rejected_on_set(impl: str) -> None:
    store = make_store(impl, FakeClock())

    with pytest.raises(ValueError, match="ttl_seconds must be positive"):
        store.set(DIGEST, "v", ttl_seconds=0)

    with pytest.raises(ValueError, match="ttl_seconds must be positive"):
        store.set(DIGEST, "v", ttl_seconds=-10)


@pytest.mark.parametrize("impl", IMPLS)
def test_non_positive_ttl_rejected_on_set_if_unchanged(impl: str) -> None:
    store = make_store(impl, FakeClock())

    with pytest.raises(ValueError, match="ttl_seconds must be positive"):
        store.set_if_unchanged(DIGEST, "old", "new", ttl_seconds=0)


@pytest.mark.parametrize("impl", IMPLS)
def test_cas_win_writes_value_and_carries_new_ttl(impl: str) -> None:
    clock = FakeClock()
    store = make_store(impl, clock)
    store.set(DIGEST, "old", ttl_seconds=60)

    assert store.set_if_unchanged(DIGEST, "old", "new", ttl_seconds=30) is True
    assert store.get(DIGEST) == "new"

    # The win must carry the new ttl, not the one from the first set.
    clock.advance(30)
    assert store.get(DIGEST) is None


@pytest.mark.parametrize("impl", IMPLS)
def test_cas_loser_writes_nothing(impl: str) -> None:
    clock = FakeClock()
    store = make_store(impl, clock)
    store.set(DIGEST, "current", ttl_seconds=60)

    assert store.set_if_unchanged(DIGEST, "stale", "new", ttl_seconds=30) is False
    # The loser must not write; the current value survives untouched.
    assert store.get(DIGEST) == "current"


def test_redis_get_decodes_raw_bytes() -> None:
    clock = FakeClock()
    fake = FakeRedis(clock)
    fake.data[f"{SESSION_KEYS}{DIGEST}"] = (b"bytes-value", None)
    store = RedisKVStore(fake, namespace=SESSION_KEYS)

    assert store.get(DIGEST) == "bytes-value"


def test_redis_namespace_lands_on_wire_keys() -> None:
    clock = FakeClock()
    fake = FakeRedis(clock)
    store = RedisKVStore(fake, namespace=SESSION_KEYS)

    store.set(DIGEST, "v", ttl_seconds=60)
    assert f"session:{DIGEST}" in fake.data


def test_shared_redis_client_keeps_keyspaces_independent() -> None:
    clock = FakeClock()
    fake = FakeRedis(clock)
    sessions = RedisKVStore(fake, namespace=SESSION_KEYS)
    tokens = RedisKVStore(fake, namespace=TOKEN_KEYS)

    sessions.set(DIGEST, "session-side", ttl_seconds=60)
    tokens.set(DIGEST, "token-side", ttl_seconds=60)

    assert sessions.get(DIGEST) == "session-side"
    assert tokens.get(DIGEST) == "token-side"
    assert f"session:{DIGEST}" in fake.data
    assert f"token:{DIGEST}" in fake.data

    sessions.delete(DIGEST)
    assert sessions.get(DIGEST) is None
    # The same digest in the other keyspace must survive the delete.
    assert tokens.get(DIGEST) == "token-side"


def test_memory_stores_with_different_namespaces_never_collide() -> None:
    clock = FakeClock()
    # Shared backing dict via constructor: the namespace prefix is the only isolation left.
    shared: dict[str, tuple[str, float]] = {}
    sessions = MemoryKVStore(SESSION_KEYS, clock=clock, entries=shared)
    tokens = MemoryKVStore(TOKEN_KEYS, clock=clock, entries=shared)

    sessions.set(DIGEST, "session-side", ttl_seconds=60)
    tokens.set(DIGEST, "token-side", ttl_seconds=60)

    assert sessions.get(DIGEST) == "session-side"
    assert tokens.get(DIGEST) == "token-side"

    # A CAS through one namespace must not see or touch the other's value.
    assert tokens.set_if_unchanged(DIGEST, "session-side", "hijack", ttl_seconds=60) is False
    assert tokens.set_if_unchanged(DIGEST, "token-side", "token-new", ttl_seconds=60) is True
    assert sessions.get(DIGEST) == "session-side"
    assert tokens.get(DIGEST) == "token-new"

    sessions.delete(DIGEST)
    assert sessions.get(DIGEST) is None
    assert tokens.get(DIGEST) == "token-new"


def test_epoch_key_and_digest_key_coexist_in_session_keyspace() -> None:
    clock = FakeClock()
    fake = FakeRedis(clock)
    store = RedisKVStore(fake, namespace=SESSION_KEYS)

    store.set(EPOCH, "2", ttl_seconds=3600)
    store.set(DIGEST, "payload", ttl_seconds=60)

    assert store.get(EPOCH) == "2"
    assert store.get(DIGEST) == "payload"
    assert f"session:{EPOCH}" in fake.data
    assert f"session:{DIGEST}" in fake.data


def test_namespace_is_required_on_both_adapters() -> None:
    with pytest.raises(TypeError, match="namespace"):
        MemoryKVStore()  # type: ignore[call-arg]

    with pytest.raises(TypeError, match="namespace"):
        RedisKVStore(FakeRedis(FakeClock()))  # type: ignore[call-arg]


def test_build_session_store_wires_session_namespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = Config.from_env({"API_REDIS_URL": "redis://localhost:6379/9"})
    captured_urls: list[str] = []
    created: list[FakeRedis] = []

    class DummyRedis:
        @classmethod
        def from_url(cls, url: str) -> FakeRedis:
            captured_urls.append(url)
            fake = FakeRedis(FakeClock())
            created.append(fake)
            return fake

    monkeypatch.setattr("api.kvstore.Redis", DummyRedis)
    store = build_session_store(cfg)

    assert isinstance(store, RedisKVStore)
    assert captured_urls == ["redis://localhost:6379/9"]
    store.set(DIGEST, "v", ttl_seconds=60)
    assert f"session:{DIGEST}" in created[0].data


def test_build_token_store_uses_kv_adapter_and_token_namespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created: list[FakeRedis] = []

    class DummyRedis:
        @classmethod
        def from_url(cls, url: str) -> FakeRedis:
            fake = FakeRedis(FakeClock())
            created.append(fake)
            return fake

    monkeypatch.setattr("api.tokens.store.Redis", DummyRedis)
    store = build_token_store()

    assert isinstance(store, RedisKVStore)
    store.set(DIGEST, "v", ttl_seconds=60)
    assert f"token:{DIGEST}" in created[0].data


def test_session_fixture_installs_kv_memory_adapter(memory_session_store) -> None:
    # Sessions resolve through the kv singleton, so the fixture must
    # install its store there, not only hand it back.
    assert isinstance(memory_session_store, MemoryKVStore)
    assert get_session_store() is memory_session_store

    memory_session_store.set(DIGEST, "v", ttl_seconds=60)
    assert f"session:{DIGEST}" in memory_session_store.entries


def test_get_and_set_session_store() -> None:
    custom_store = MemoryKVStore(SESSION_KEYS)
    set_session_store(custom_store)
    try:
        assert get_session_store() is custom_store
    finally:
        set_session_store(None)
