"""Scope machinery: flush guard, request middleware, lifespan check."""

import pytest
from api.db import Base
from api.dek_store import PostgresDekStore
from api.main import app
from api.models import TenantDek, User, UserTenant
from api.models.encrypted_string import EncryptedString
from conftest import create_user
from crypto import tenant_scope
from crypto.errors import CryptoCategory, CryptoError
from fastapi.testclient import TestClient
from sqlalchemy import Column, Integer, Table, select


def _dek(tenant_id: str) -> TenantDek:
    return TenantDek(tenant_id=tenant_id, key_id="k", wrapped_dek="w" * 20)


def test_flush_guard_rejects_tenant_write_without_scope(session_factory):
    with session_factory() as db:
        db.add(_dek("tenant-x"))
        with pytest.raises(CryptoError) as err:
            db.flush()
        db.rollback()
        assert db.get(TenantDek, "tenant-x") is None
    assert err.value.category == CryptoCategory.MISSING_TENANT_SCOPE


def test_flush_guard_rejects_mismatched_scope(session_factory):
    with session_factory() as db, tenant_scope("tenant-y"):
        db.add(_dek("tenant-x"))
        with pytest.raises(CryptoError):
            db.flush()
        db.rollback()
        assert db.get(TenantDek, "tenant-x") is None


def test_flush_guard_allows_matching_scope(session_factory):
    with session_factory() as db, tenant_scope("tenant-x"):
        db.add(_dek("tenant-x"))
        db.flush()
        assert db.get(TenantDek, "tenant-x") is not None


def test_dek_store_put_scopes_its_own_write(session_factory):
    store = PostgresDekStore(session_factory, "key-id-1")
    stored = store.put("tenant-z", "wrapped-dek-value-xxxx")
    assert stored == "wrapped-dek-value-xxxx"
    with session_factory() as db:
        assert db.get(TenantDek, "tenant-z") is not None


def test_register_link_write_passes_the_guard(client, session_factory):
    resp = client.post("/api/setup", json={"email": "g@x.com", "password": "p"})
    assert resp.status_code == 201


def test_lifespan_refuses_encrypted_columns_without_module(monkeypatch):
    table = Table(
        "tmp_secret",
        Base.metadata,
        Column("id", Integer, primary_key=True),
        Column("secret", EncryptedString),
    )
    monkeypatch.setattr("api.main.build_and_register_field_crypto", lambda: None)
    try:
        probe = TestClient(app)
        with pytest.raises(RuntimeError, match="crypto module"):
            # __enter__ runs the lifespan; the crypto check must raise.
            probe.__enter__()
    finally:
        Base.metadata.remove(table)


def test_me_reads_tenant_from_ambient_scope(client, session_factory):
    client.post("/api/setup", json={"email": "amb@x.com", "password": "p"})
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    with session_factory() as db:
        link = db.scalar(select(UserTenant).join(User, User.id == UserTenant.user_id))
    assert me.json()["tenant_id"] == link.tenant_id


def test_me_never_reports_another_users_tenant(client, session_factory):
    client.post("/api/setup", json={"email": "one@x.com", "password": "p"})
    first = client.get("/api/auth/me").json()["tenant_id"]
    create_user(client, "two@x.com", "p")
    login = client.post("/api/auth/login", json={"email": "two@x.com", "password": "p"})
    assert login.status_code == 204
    second = client.get("/api/auth/me").json()["tenant_id"]
    assert first != second


def test_tenant_scope_middleware_resolves_without_db():
    from api import sessions
    from api.middleware import TenantScopeMiddleware
    from crypto import current_tenant
    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route

    token = sessions.mint(user_id=1, tenant_id="scoped-123")
    captured_tenant = None

    async def endpoint(request):
        nonlocal captured_tenant
        captured_tenant = current_tenant()
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/", endpoint)])
    app.add_middleware(TenantScopeMiddleware)
    client = TestClient(app)
    client.cookies.set(sessions.COOKIE_NAME, token)
    resp = client.get("/")
    assert resp.status_code == 200
    assert captured_tenant == "scoped-123"
