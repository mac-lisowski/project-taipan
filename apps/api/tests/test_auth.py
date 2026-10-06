import hashlib

from api.models import AuthSession, Tenant, User, UserTenant
from sqlalchemy import func, select


def _counts(db):
    users = db.scalar(select(func.count()).select_from(User))
    links = db.scalar(select(func.count()).select_from(UserTenant))
    tenants = db.scalar(select(func.count()).select_from(Tenant))
    return users, links, tenants


def test_register_creates_tenant_user_link_and_session(client, session_factory):
    resp = client.post(
        "/api/auth/register", json={"email": "ada@example.com", "password": "s3cret123"}
    )
    assert resp.status_code == 201
    cookie = resp.headers["set-cookie"]
    assert "session=" in cookie
    assert "httponly" in cookie.lower()
    assert "samesite=lax" in cookie.lower()
    assert "path=/" in cookie.lower()
    assert "; secure" not in cookie.lower()
    token = resp.cookies.get("session")
    assert token is not None
    with session_factory() as db:
        users, links, tenants = _counts(db)
        assert users == links == tenants == 1
        link = db.scalar(select(UserTenant))
        user = db.scalar(select(User))
        tenant = db.scalar(select(Tenant))
        assert link is not None and user is not None and tenant is not None
        assert link.user_id == user.id
        assert link.tenant_id == tenant.id
        sess = db.get(AuthSession, hashlib.sha256(token.encode()).hexdigest())
        assert sess is not None
        assert sess.user_id == user.id


def test_create_user_endpoint_also_creates_tenant_and_link(client, session_factory):
    resp = client.post("/api/users", json={"email": "b@example.com", "password": "p"})
    assert resp.status_code == 201
    with session_factory() as db:
        assert _counts(db) == (1, 1, 1)
        link = db.scalar(select(UserTenant))
        assert link is not None
        assert link.tenant_id == db.scalar(select(Tenant.id))


def test_auth_register_duplicate_email_returns_409(client):
    client.post("/api/auth/register", json={"email": "d@example.com", "password": "p"})
    resp = client.post("/api/auth/register", json={"email": "d@example.com", "password": "p"})
    assert resp.status_code == 409
