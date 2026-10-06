import pytest
from api import authz
from api.models import Role, User, UserRole
from fastapi import HTTPException
from sqlalchemy import select
from starlette.requests import Request


def _request_with_cookie(token=None):
    headers = []
    if token is not None:
        headers.append((b"cookie", f"session={token}".encode()))
    return Request({"type": "http", "headers": headers})


def _register(client, email):
    resp = client.post("/api/auth/register", json={"email": email, "password": "s3cret123"})
    assert resp.status_code == 201
    return resp.cookies.get("session")


def test_require_admin_without_session_returns_401(client, session_factory):
    with session_factory() as db, pytest.raises(HTTPException) as exc:
        authz.require_admin(_request_with_cookie(), db)
    assert exc.value.status_code == 401


def test_require_admin_without_role_returns_403(client, session_factory):
    token = _register(client, "plain@example.com")
    with session_factory() as db, pytest.raises(HTTPException) as exc:
        authz.require_admin(_request_with_cookie(token), db)
    assert exc.value.status_code == 403


def test_require_admin_with_admin_role_passes(client, session_factory):
    token = _register(client, "boss@example.com")
    with session_factory() as db:
        user_id = db.scalar(select(User.id).where(User.email == "boss@example.com"))
        db.add(UserRole(user_id=user_id, role=Role.ADMIN))
        db.commit()
    with session_factory() as db:
        user = authz.require_admin(_request_with_cookie(token), db)
        assert user.email == "boss@example.com"


def test_register_grants_member_role_by_default(client):
    _register(client, "regular@example.com")
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["roles"] == ["member"]


def test_me_returns_roles_for_admin(client, session_factory):
    _register(client, "admin@example.com")
    with session_factory() as db:
        user_id = db.scalar(select(User.id).where(User.email == "admin@example.com"))
        db.add(UserRole(user_id=user_id, role=Role.ADMIN))
        db.commit()
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["roles"] == ["admin", "member"]
