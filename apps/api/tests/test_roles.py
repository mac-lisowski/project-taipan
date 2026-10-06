import pytest
from api import authz
from fastapi import HTTPException
from starlette.requests import Request


def _request_with_cookie(token=None):
    headers = []
    if token is not None:
        headers.append((b"cookie", f"session={token}".encode()))
    return Request({"type": "http", "headers": headers})


def _setup(client, email):
    resp = client.post("/api/setup", json={"email": email, "password": "s3cret123"})
    assert resp.status_code == 201
    return resp.cookies.get("session")


def _login(client, email):
    resp = client.post("/api/auth/login", json={"email": email, "password": "s3cret123"})
    assert resp.status_code == 204
    return resp.cookies.get("session")


def test_require_admin_without_session_returns_401(client, session_factory):
    with session_factory() as db, pytest.raises(HTTPException) as exc:
        authz.require_admin(_request_with_cookie(), db)
    assert exc.value.status_code == 401


def test_require_admin_without_role_returns_403(client, session_factory):
    created = client.post(
        "/api/users", json={"email": "plain@example.com", "password": "s3cret123"}
    )
    assert created.status_code == 201
    token = _login(client, "plain@example.com")
    with session_factory() as db, pytest.raises(HTTPException) as exc:
        authz.require_admin(_request_with_cookie(token), db)
    assert exc.value.status_code == 403


def test_require_admin_with_admin_role_passes(client, session_factory):
    token = _setup(client, "boss@example.com")
    with session_factory() as db:
        user = authz.require_admin(_request_with_cookie(token), db)
        assert user.email == "boss@example.com"


def test_register_grants_member_role_by_default(client):
    created = client.post(
        "/api/users", json={"email": "regular@example.com", "password": "s3cret123"}
    )
    assert created.status_code == 201
    _login(client, "regular@example.com")
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["roles"] == ["member"]


def test_me_returns_roles_for_admin(client):
    _setup(client, "admin@example.com")
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["roles"] == ["admin", "member"]
