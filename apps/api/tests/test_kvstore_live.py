"""Live proof: RedisKVStore against a real Redis.

Skip when Redis is unreachable, same convention as
test_field_crypto_live.py. What only a live run proves: the real Lua
CAS, real EX TTLs, real bytes on the wire, and two namespaces sharing
one client. Expiry itself is Redis's contract; the adapter's job is to
hand Redis a TTL, so the tests check TTL presence, not the clock.
"""

import os
import uuid
from typing import NamedTuple

import pytest
from api.kvstore import RedisKVStore
from redis import Redis, RedisError

REDIS_URL = os.environ.get("API_REDIS_URL", "redis://localhost:6379/0")


def _reachable() -> bool:
    # redis-py raises RedisError, not OSError, on connect failures.
    try:
        return bool(Redis.from_url(REDIS_URL, socket_connect_timeout=2).ping())
    except (OSError, RedisError):
        return False


live_only = pytest.mark.skipif(not _reachable(), reason="redis not reachable")


class Handle(NamedTuple):
    store: RedisKVStore
    client: Redis
    namespace: str


@pytest.fixture
def handle() -> Handle:
    # A unique namespace per run keeps the live database collision-free.
    namespace = f"kvstore-live:{uuid.uuid4().hex}:"
    client = Redis.from_url(REDIS_URL)
    store = RedisKVStore(client, namespace=namespace)
    yield Handle(store, client, namespace)
    for key in client.scan_iter(f"{namespace}*"):
        client.delete(key)


@live_only
def test_roundtrip_decodes_live_bytes(handle: Handle) -> None:
    handle.store.set("digest-a", "v1", ttl_seconds=60)
    assert handle.store.get("digest-a") == "v1"


@live_only
def test_delete_of_missing_key_is_noop(handle: Handle) -> None:
    handle.store.delete("digest-never-written")
    assert handle.store.get("digest-never-written") is None


@live_only
def test_cas_win_writes_new_value_with_new_ttl(handle: Handle) -> None:
    handle.store.set("digest-cas", "old", ttl_seconds=60)
    won = handle.store.set_if_unchanged("digest-cas", "old", "new", ttl_seconds=120)
    assert won is True
    assert handle.store.get("digest-cas") == "new"
    assert 0 < handle.client.ttl(f"{handle.namespace}digest-cas") <= 120


@live_only
def test_cas_loser_leaves_value_and_ttl_alone(handle: Handle) -> None:
    handle.store.set("digest-cas", "kept", ttl_seconds=60)
    won = handle.store.set_if_unchanged("digest-cas", "stale", "new", ttl_seconds=120)
    assert won is False
    assert handle.store.get("digest-cas") == "kept"
    assert 0 < handle.client.ttl(f"{handle.namespace}digest-cas") <= 60


@live_only
def test_set_lands_under_namespaced_key_with_ttl(handle: Handle) -> None:
    handle.store.set("digest-a", "v1", ttl_seconds=90)
    assert handle.client.exists(f"{handle.namespace}digest-a") == 1
    assert 0 < handle.client.ttl(f"{handle.namespace}digest-a") <= 90


@live_only
def test_namespaces_coexist_on_one_live_client(handle: Handle) -> None:
    other = RedisKVStore(handle.client, namespace=f"{handle.namespace}token:")
    handle.store.set("same-digest", "session-side", ttl_seconds=60)
    other.set("same-digest", "token-side", ttl_seconds=60)
    assert handle.store.get("same-digest") == "session-side"
    assert other.get("same-digest") == "token-side"
    assert other.set_if_unchanged("same-digest", "session-side", "x", ttl_seconds=60) is False
    assert handle.store.get("same-digest") == "session-side"
    handle.store.delete("same-digest")
    assert other.get("same-digest") == "token-side"
