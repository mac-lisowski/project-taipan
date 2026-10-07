"""Tests for api.sessions module and SessionData resolution."""

import json

import pytest
from api import sessions
from api.config import DEFAULT_SESSION_TTL_SECONDS
from api.kvstore import SESSION_KEYS, KVStore, MemoryKVStore, RedisKVStore
from api_testsupport import FakeClock, FakeRedis


def _memory_store(clock: FakeClock) -> KVStore:
    return MemoryKVStore(SESSION_KEYS, clock=clock)


def _redis_store(clock: FakeClock) -> KVStore:
    return RedisKVStore(FakeRedis(clock), namespace="sess:")


def test_mint_and_resolve() -> None:
    store = MemoryKVStore(SESSION_KEYS)
    token = sessions.mint(user_id=42, tenant_id="tenant-abc", store=store, ttl_seconds=300)
    assert isinstance(token, str)

    data = sessions.resolve(token, store=store)
    assert data is not None
    assert data.user_id == 42
    assert data.tenant_id == "tenant-abc"


def test_resolve_missing_returns_none() -> None:
    store = MemoryKVStore(SESSION_KEYS)
    assert sessions.resolve("nonexistent-token", store=store) is None


def test_resolve_corrupt_payload_returns_none() -> None:
    store = MemoryKVStore(SESSION_KEYS)
    token = sessions.mint(user_id=1, tenant_id="t1", store=store)
    digest = sessions._digest(token)

    # Invalid JSON
    store.set(digest, "not-json", ttl_seconds=60)
    assert sessions.resolve(token, store=store) is None

    # Valid JSON that is not an object
    store.set(digest, "[]", ttl_seconds=60)
    assert sessions.resolve(token, store=store) is None

    # Missing keys
    store.set(digest, json.dumps({"user_id": 1}), ttl_seconds=60)
    assert sessions.resolve(token, store=store) is None

    # Invalid types
    store.set(digest, json.dumps({"user_id": "not-an-int", "tenant_id": "t1"}), ttl_seconds=60)
    assert sessions.resolve(token, store=store) is None


def test_revoke_removes_session() -> None:
    store = MemoryKVStore(SESSION_KEYS)
    token = sessions.mint(user_id=99, tenant_id="t-99", store=store)
    assert sessions.resolve(token, store=store) is not None

    sessions.revoke(token, store=store)
    assert sessions.resolve(token, store=store) is None


def test_revoke_all_kills_user_sessions_and_new_mint_works() -> None:
    store = MemoryKVStore(SESSION_KEYS)
    first = sessions.mint(user_id=1, tenant_id="t-1", store=store)
    second = sessions.mint(user_id=1, tenant_id="t-1", store=store)
    other = sessions.mint(user_id=2, tenant_id="t-2", store=store)

    sessions.revoke_all(user_id=1, store=store)

    assert sessions.resolve(first, store=store) is None
    assert sessions.resolve(second, store=store) is None
    assert sessions.resolve(other, store=store) is not None
    assert sessions.resolve(other, store=store).tenant_id == "t-2"

    fresh = sessions.mint(user_id=1, tenant_id="t-1", store=store)
    data = sessions.resolve(fresh, store=store)
    assert data is not None
    assert data.user_id == 1
    assert data.tenant_id == "t-1"


def test_revoke_all_after_single_revoke_kills_remaining_sessions() -> None:
    store = MemoryKVStore(SESSION_KEYS)
    revoked = sessions.mint(user_id=3, tenant_id="t-3", store=store)
    remaining = sessions.mint(user_id=3, tenant_id="t-3", store=store)

    sessions.revoke(revoked, store=store)
    sessions.revoke_all(user_id=3, store=store)

    assert sessions.resolve(revoked, store=store) is None
    assert sessions.resolve(remaining, store=store) is None


def test_revoke_all_for_unknown_user_spares_other_sessions() -> None:
    store = MemoryKVStore(SESSION_KEYS)
    token = sessions.mint(user_id=5, tenant_id="t-5", store=store)

    sessions.revoke_all(user_id=6, store=store)

    data = sessions.resolve(token, store=store)
    assert data is not None
    assert data.user_id == 5


def test_revoke_all_kills_sessions_minted_before_epoch_tracking() -> None:
    store = MemoryKVStore(SESSION_KEYS)
    token = sessions.mint(user_id=8, tenant_id="t-8", store=store)

    # Simulate a pre-deploy record by stripping its epoch field.
    digest = sessions._digest(token)
    record = json.loads(store.get(digest))
    record.pop("epoch")
    store.set(digest, json.dumps(record), ttl_seconds=300)
    assert sessions.resolve(token, store=store) is not None

    sessions.revoke_all(user_id=8, store=store)
    assert sessions.resolve(token, store=store) is None


def test_mint_missing_epoch_after_revoke_fails_closed() -> None:
    store = MemoryKVStore(SESSION_KEYS)
    user_id = 9

    # A mint that read no epoch before revoke_all wrote it would embed
    # none; the record must not resolve after the revoke lands.
    stale_payload = json.dumps({"user_id": user_id, "tenant_id": "t-9"})
    store.set(sessions._digest("stale-token"), stale_payload, ttl_seconds=300)
    sessions.revoke_all(user_id, store=store)

    assert sessions.resolve("stale-token", store=store) is None


def test_mint_stale_epoch_after_revoke_fails_closed() -> None:
    store = MemoryKVStore(SESSION_KEYS)
    user_id = 12

    sessions.revoke_all(user_id, store=store)
    stale_epoch = sessions._current_epoch(store, user_id)
    sessions.revoke_all(user_id, store=store)

    # A mint that read the first epoch before the second revoke and
    # writes after it must not survive that second revoke.
    payload = json.dumps({"user_id": user_id, "tenant_id": "t-12", "epoch": stale_epoch})
    store.set(sessions._digest("late-token"), payload, ttl_seconds=300)

    assert sessions.resolve("late-token", store=store) is None


def test_short_mint_ttl_does_not_shorten_epoch_ttl() -> None:
    clock = FakeClock()
    store = MemoryKVStore(SESSION_KEYS, clock=clock)
    user_id = 13

    sessions.revoke_all(user_id, store=store)
    long_lived = sessions.mint(user_id, "t-13", store=store, ttl_seconds=5000)
    sessions.mint(user_id, "t-13", store=store, ttl_seconds=5)

    clock.advance(50)

    # The short mint must not drag the epoch below the long session.
    data = sessions.resolve(long_lived, store=store)
    assert data is not None
    assert data.user_id == user_id


@pytest.mark.parametrize("make_store", [_memory_store, _redis_store], ids=["memory", "redis"])
def test_revoke_all_reaches_long_session_after_short_mint_expires(make_store) -> None:
    # A shared per-user index refreshed per mint would lapse with the
    # short session and strand the long one from revoke-all.
    clock = FakeClock()
    store = make_store(clock)
    user_id = 14

    sessions.revoke_all(user_id, store=store)
    long_lived = sessions.mint(user_id, "t-14", store=store, ttl_seconds=5000)
    short_lived = sessions.mint(user_id, "t-14", store=store, ttl_seconds=5)
    other = sessions.mint(user_id + 1, "t-15", store=store, ttl_seconds=5000)

    clock.advance(50)
    assert sessions.resolve(short_lived, store=store) is None
    assert sessions.resolve(long_lived, store=store) is not None

    sessions.revoke_all(user_id, store=store)

    assert sessions.resolve(long_lived, store=store) is None
    assert sessions.resolve(other, store=store) is not None


def test_tenant_id_for_token() -> None:
    store = MemoryKVStore(SESSION_KEYS)
    token = sessions.mint(user_id=7, tenant_id="tenant-777", store=store)

    assert sessions.tenant_id_for_token(token, store=store) == "tenant-777"
    assert sessions.tenant_id_for_token("unknown", store=store) is None


def test_mint_uses_default_ttl() -> None:
    clock = FakeClock()
    store = MemoryKVStore(SESSION_KEYS, clock=clock)
    token = sessions.mint(user_id=10, tenant_id="t-10", store=store)

    # Entry exists now
    assert sessions.resolve(token, store=store) is not None

    # Mint must apply the configured default: one second before it
    # elapses the session still resolves, at the boundary it does not.
    clock.advance(DEFAULT_SESSION_TTL_SECONDS - 1)
    assert sessions.resolve(token, store=store) is not None

    clock.advance(1)
    assert sessions.resolve(token, store=store) is None


def test_session_cookie_helpers() -> None:
    from fastapi import Response

    resp = Response()
    sessions.set_session_cookie(resp, "test-token")
    raw = resp.headers.get("set-cookie", "")
    assert "session=test-token" in raw
    assert "httponly" in raw.lower()
    assert "samesite=lax" in raw.lower()
    assert "path=/" in raw.lower()

    clear_resp = Response()
    sessions.clear_session_cookie(clear_resp)
    clear_raw = clear_resp.headers.get("set-cookie", "").lower()
    assert 'session=""' in clear_raw
    assert "max-age=0" in clear_raw
