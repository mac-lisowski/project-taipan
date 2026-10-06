import hashlib
from datetime import UTC, datetime, timedelta

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


def test_login_returns_204_and_cookie_and_me_returns_tenant(client, session_factory):
    reg = client.post(
        "/api/auth/register", json={"email": "li@example.com", "password": "s3cret123"}
    )
    assert reg.status_code == 201
    user_id = reg.json()["id"]

    resp = client.post("/api/auth/login", json={"email": "li@example.com", "password": "s3cret123"})
    assert resp.status_code == 204
    assert resp.cookies.get("session") is not None

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    body = me.json()
    assert body["id"] == user_id
    assert body["email"] == "li@example.com"
    with session_factory() as db:
        expected = db.scalar(select(UserTenant.tenant_id))
    assert body["tenant_id"] == expected


def test_login_unknown_email_returns_401(client):
    resp = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "p"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "invalid email or password"


def test_login_wrong_password_returns_401(client):
    client.post("/api/auth/register", json={"email": "w@example.com", "password": "right"})
    resp = client.post("/api/auth/login", json={"email": "w@example.com", "password": "wrong"})
    assert resp.status_code == 401
    assert "session" not in resp.headers.get("set-cookie", "")


def test_logout_deletes_session_and_clears_cookie(client, session_factory):
    client.post("/api/auth/register", json={"email": "lo@example.com", "password": "p"})
    assert client.get("/api/auth/me").status_code == 200

    resp = client.post("/api/auth/logout")
    assert resp.status_code == 204
    assert client.cookies.get("session") is None
    assert client.get("/api/auth/me").status_code == 401
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(AuthSession)) == 0


def test_logout_without_session_returns_204(client):
    assert client.post("/api/auth/logout").status_code == 204


def test_me_without_session_returns_401(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_session_without_link_returns_401(client, session_factory):
    client.post("/api/auth/register", json={"email": "nl@example.com", "password": "p"})
    with session_factory() as db:
        db.execute(UserTenant.__table__.delete())
        db.commit()
    assert client.get("/api/auth/me").status_code == 401


def test_expired_session_behaves_like_no_session(client, session_factory):
    client.post("/api/auth/register", json={"email": "ex@example.com", "password": "p"})
    with session_factory() as db:
        db.execute(
            AuthSession.__table__.update().values(expires_at=datetime.now(UTC) - timedelta(hours=1))
        )
        db.commit()
    assert client.get("/api/auth/me").status_code == 401
