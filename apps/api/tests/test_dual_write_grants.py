"""Dual-write grants: setup and user creation also fill the new tables."""

import pytest
from api.models import SystemRole, Tenant, User, UserSystemRole, UserTenant, UserTenantRole
from conftest import create_user, setup_admin
from crypto import tenant_scope
from crypto.errors import CryptoCategory, CryptoError
from sqlalchemy import select


def test_setup_grants_admin_member_and_system_owner(client, session_factory):
    resp = client.post("/api/setup", json={"email": "op@example.com", "password": "s3cret123"})
    assert resp.status_code == 201
    user_id = resp.json()["id"]
    with session_factory() as db:
        tenant_id = db.scalar(select(UserTenant.tenant_id).where(UserTenant.user_id == user_id))
        grants = db.scalars(
            select(UserTenantRole.role).where(UserTenantRole.user_id == user_id)
        ).all()
        grant_tenants = db.scalars(
            select(UserTenantRole.tenant_id).where(UserTenantRole.user_id == user_id)
        ).all()
        system = db.scalars(
            select(UserSystemRole.role).where(UserSystemRole.user_id == user_id)
        ).all()
    assert sorted(grants) == ["admin", "member"]
    assert grant_tenants == [tenant_id, tenant_id]
    assert system == [SystemRole.SYSTEM_OWNER.value]


def test_created_user_holds_member_in_own_tenant(client, session_factory):
    setup_admin(client, "admin@x.com")
    user_id = create_user(client, "new@x.com")
    with session_factory() as db:
        tenant_id = db.scalar(select(UserTenant.tenant_id).where(UserTenant.user_id == user_id))
        rows = db.scalars(select(UserTenantRole).where(UserTenantRole.user_id == user_id)).all()
    assert [(row.role, row.tenant_id) for row in rows] == [("member", tenant_id)]


def test_tenant_role_write_without_scope_raises(session_factory):
    with session_factory() as db:
        db.add(UserTenantRole(user_id=1, tenant_id="tenant-x", role="member"))
        with pytest.raises(CryptoError) as err:
            db.flush()
    assert err.value.category == CryptoCategory.MISSING_TENANT_SCOPE


def test_tenant_role_write_inside_matching_scope_passes(session_factory):
    with session_factory() as db, tenant_scope("tenant-x"):
        db.add(Tenant(id="tenant-x"))
        user = User(email="guard@x.com", hashed_password="x")
        db.add(user)
        db.flush()
        db.add(UserTenantRole(user_id=user.id, tenant_id="tenant-x", role="member"))
        db.flush()
        assert db.scalars(select(UserTenantRole.role)).all() == ["member"]


def test_system_role_write_needs_no_scope(session_factory):
    with session_factory() as db:
        user = User(email="sys@x.com", hashed_password="x")
        db.add(user)
        db.flush()
        db.add(UserSystemRole(user_id=user.id, role="system_owner"))
        db.flush()
        assert db.scalars(select(UserSystemRole.role)).all() == ["system_owner"]
