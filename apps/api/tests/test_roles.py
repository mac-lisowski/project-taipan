import pytest
from api import authz
from api.models import Tenant, User, UserTenant, UserTenantRole
from api_testsupport import create_user, login, setup_admin
from crypto import tenant_scope
from fastapi import HTTPException
from sqlalchemy import delete, select
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


def test_me_returns_tenant_roles_and_system_roles_for_admin(client):
    setup_admin(client, "owner@example.com")
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    body = me.json()
    assert body["roles"] == ["admin", "member"]
    assert body["system_roles"] == ["system_owner"]


def test_me_returns_empty_system_roles_for_member(client):
    setup_admin(client)
    create_user(client, "member@example.com")
    login(client, "member@example.com")
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    body = me.json()
    assert body["roles"] == ["member"]
    assert body["system_roles"] == []


def test_admin_role_for_another_tenant_does_not_unlock_users(client, session_factory):
    setup_admin(client)
    create_user(client, "cross@example.com")
    login(client, "cross@example.com")
    with session_factory() as db, tenant_scope("tenant-other"):
        db.add(Tenant(id="tenant-other"))
        user_id = db.scalar(select(User.id).where(User.email == "cross@example.com"))
        db.add(UserTenantRole(user_id=user_id, tenant_id="tenant-other", role="admin"))
        db.commit()
    assert client.get("/api/users").status_code == 403
    assert client.get("/api/auth/me").json()["roles"] == ["member"]


def test_me_reflects_tenant_role_rows_deleted_under_live_session(client, session_factory):
    setup_admin(client, "owner@example.com")
    login(client, "owner@example.com")
    with session_factory() as db:
        db.execute(delete(UserTenantRole))
        db.commit()
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    body = me.json()
    assert body["roles"] == []
    assert body["system_roles"] == ["system_owner"]


def test_can_answers_tenant_role_only_for_that_tenant(client, session_factory):
    setup_admin(client, "can@x.com")
    create_user(client, "crew@x.com")
    with session_factory() as db:
        owner_id = db.scalar(select(User.id).where(User.email == "can@x.com"))
        crew_id = db.scalar(select(User.id).where(User.email == "crew@x.com"))
        owner_tenant = db.scalar(select(UserTenant.tenant_id).where(UserTenant.user_id == owner_id))

        assert authz.can(db, owner_id, "admin", owner_tenant) is True
        assert authz.can(db, owner_id, "member", owner_tenant) is True
        assert not authz.can(db, owner_id, "admin", "tenant-nowhere")
        assert not authz.can(db, crew_id, "admin", owner_tenant)


def test_can_answers_system_role_without_tenant(client, session_factory):
    setup_admin(client, "sysonly@x.com")
    create_user(client, "plain@x.com")
    with session_factory() as db:
        owner_id = db.scalar(select(User.id).where(User.email == "sysonly@x.com"))
        plain_id = db.scalar(select(User.id).where(User.email == "plain@x.com"))

        assert authz.can(db, owner_id, "system_owner", None) is True
        assert not authz.can(db, plain_id, "system_owner", None)


def test_require_system_owner_blocks_member(client, session_factory):
    setup_admin(client, "gate@x.com")
    create_user(client, "member@x.com")
    token = login(client, "member@x.com")
    with session_factory() as db:
        principal = authz.current_principal(_request_with_cookie(token), db)
        with pytest.raises(HTTPException) as exc:
            authz.require_system_owner(principal)
        assert exc.value.status_code == 403


def test_require_system_owner_passes_for_owner(client, session_factory):
    setup_admin(client, "holder@x.com")
    token = login(client, "holder@x.com")
    with session_factory() as db:
        principal = authz.current_principal(_request_with_cookie(token), db)
        allowed = authz.require_system_owner(principal)
        assert allowed.email == "holder@x.com"
