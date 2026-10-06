import pytest
from api import authz
from conftest import create_user, login, setup_admin
from fastapi import HTTPException
from starlette.requests import Request


def _request_with_cookie(token=None):
    headers = []
    if token is not None:
        headers.append((b"cookie", f"session={token}".encode()))
    return Request({"type": "http", "headers": headers})


def test_current_principal_without_session_returns_401(client, session_factory):
    with session_factory() as db, pytest.raises(HTTPException) as exc:
        authz.current_principal(_request_with_cookie(), db)
    assert exc.value.status_code == 401


def test_require_admin_without_role_returns_403(client, session_factory):
    setup_admin(client, "admin@example.com")
    create_user(client, "plain@example.com")
    token = login(client, "plain@example.com")
    with session_factory() as db:
        principal = authz.current_principal(_request_with_cookie(token), db)
        with pytest.raises(HTTPException) as exc:
            authz.require_admin(principal)
        assert exc.value.status_code == 403


def test_require_admin_with_admin_role_passes(client, session_factory):
    setup_admin(client, "boss@example.com")
    token = login(client, "boss@example.com")
    with session_factory() as db:
        principal = authz.current_principal(_request_with_cookie(token), db)
        admin = authz.require_admin(principal)
        assert isinstance(admin, authz.Principal)
        assert admin.email == "boss@example.com"
        assert admin.has_role("admin")


def test_principal_is_immutable():
    from dataclasses import FrozenInstanceError

    principal = authz.Principal(user_id=1, email="a@b.com", tenant_id="t1", roles=("admin",))
    field = "email"
    with pytest.raises(FrozenInstanceError):
        setattr(principal, field, "changed@b.com")


def test_current_principal_missing_user_returns_401(client, session_factory):
    from api import sessions

    token = sessions.mint(user_id=999999, tenant_id="tenant_x")
    with session_factory() as db, pytest.raises(HTTPException) as exc:
        authz.current_principal(_request_with_cookie(token), db)
    assert exc.value.status_code == 401


def test_register_grants_member_role_by_default(client):
    setup_admin(client)
    create_user(client, "regular@example.com")
    login(client, "regular@example.com")
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["roles"] == ["member"]


def test_me_returns_roles_for_admin(client):
    setup_admin(client, "admin@example.com")
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["roles"] == ["admin", "member"]


def test_route_require_admin_without_session_returns_401(client):
    assert client.get("/api/users").status_code == 401


def test_route_require_admin_without_admin_role_returns_403(client):
    setup_admin(client)
    create_user(client, "regular2@example.com")
    login(client, "regular2@example.com")
    assert client.get("/api/users").status_code == 403


def test_route_require_admin_with_admin_role_succeeds(client):
    setup_admin(client, "superadmin@example.com")
    login(client, "superadmin@example.com")
    assert client.get("/api/users").status_code == 200
