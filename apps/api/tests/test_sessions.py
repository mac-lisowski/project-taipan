"""Tests for api.sessions module and SessionData resolution."""

import json

from api import sessions
from api.session_store import MemorySessionStore


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_mint_and_resolve() -> None:
    store = MemorySessionStore()
    token = sessions.mint(user_id=42, tenant_id="tenant-abc", store=store, ttl_seconds=300)
    assert isinstance(token, str)

    data = sessions.resolve(token, store=store)
    assert data is not None
    assert data.user_id == 42
    assert data.tenant_id == "tenant-abc"


def test_resolve_missing_returns_none() -> None:
    store = MemorySessionStore()
    assert sessions.resolve("nonexistent-token", store=store) is None


def test_resolve_corrupt_payload_returns_none() -> None:
    store = MemorySessionStore()
    token = sessions.mint(user_id=1, tenant_id="t1", store=store)
    digest = sessions._digest(token)

    # Invalid JSON
    store.set(digest, "not-json", ttl_seconds=60)
    assert sessions.resolve(token, store=store) is None

    # Missing keys
    store.set(digest, json.dumps({"user_id": 1}), ttl_seconds=60)
    assert sessions.resolve(token, store=store) is None

    # Invalid types
    store.set(digest, json.dumps({"user_id": "not-an-int", "tenant_id": "t1"}), ttl_seconds=60)
    assert sessions.resolve(token, store=store) is None


def test_revoke_removes_session() -> None:
    store = MemorySessionStore()
    token = sessions.mint(user_id=99, tenant_id="t-99", store=store)
    assert sessions.resolve(token, store=store) is not None

    sessions.revoke(token, store=store)
    assert sessions.resolve(token, store=store) is None


def test_tenant_id_for_token() -> None:
    store = MemorySessionStore()
    token = sessions.mint(user_id=7, tenant_id="tenant-777", store=store)

    assert sessions.tenant_id_for_token(token, store=store) == "tenant-777"
    assert sessions.tenant_id_for_token("unknown", store=store) is None


def test_mint_uses_default_ttl() -> None:
    clock = FakeClock()
    store = MemorySessionStore(clock=clock)
    token = sessions.mint(user_id=10, tenant_id="t-10", store=store)

    # Entry exists now
    assert sessions.resolve(token, store=store) is not None

    # Advance beyond default ttl (14 days = 1,209,600s)
    clock.advance(1_209_601)
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

    sessions.clear_session_cookie(resp)
    # Deleting cookie expires it
    assert "session=" in resp.headers.get("set-cookie", "")
