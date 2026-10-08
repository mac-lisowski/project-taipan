"""Owner delete over HTTP: refuse self, revoke, cascade."""

from api.models import Tenant, UserTenant
from conftest import create_user, login, setup_admin
from sqlalchemy import select


def test_delete_refuses_self(client):
    admin_id = setup_admin(client, "admin@x.com")

    resp = client.delete(f"/api/users/{admin_id}")

    assert resp.status_code == 409
    assert resp.json()["detail"] == "cannot change your own account"


def test_delete_kills_victim_session(client):
    setup_admin(client, "admin@x.com")
    victim = create_user(client, "victim@x.com")
    token = login(client, "victim@x.com")
    login(client, "admin@x.com")

    assert client.delete(f"/api/users/{victim}").status_code == 204

    assert client.get("/api/auth/me", headers={"Cookie": f"session={token}"}).status_code == 401


def test_delete_removes_personal_tenant(client, session_factory):
    setup_admin(client, "admin@x.com")
    victim = create_user(client, "victim@x.com")
    with session_factory() as session:
        tenant_id = session.scalar(select(UserTenant.tenant_id).where(UserTenant.user_id == victim))
    assert tenant_id is not None

    assert client.delete(f"/api/users/{victim}").status_code == 204

    with session_factory() as session:
        assert session.get(Tenant, tenant_id) is None
