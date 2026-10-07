from api import sessions
from api.models import Tenant, User, UserTenant
from sqlalchemy import func, select


def _counts(db):
    users = db.scalar(select(func.count()).select_from(User))
    links = db.scalar(select(func.count()).select_from(UserTenant))
    tenants = db.scalar(select(func.count()).select_from(Tenant))
    return users, links, tenants


def test_setup_creates_tenant_user_link_and_session(client, session_factory):
    resp = client.post("/api/setup", json={"email": "ada@example.com", "password": "s3cret123"})
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
        sess = sessions.resolve(token)
        assert sess is not None
        assert sess.user_id == user.id
        assert sess.tenant_id == tenant.id


def test_create_user_endpoint_also_creates_tenant_and_link(admin_client, session_factory):
    resp = admin_client.post("/api/users", json={"email": "b@example.com", "password": "s3cret123"})
    assert resp.status_code == 201
    with session_factory() as db:
        assert _counts(db) == (2, 2, 2)


def test_login_returns_204_and_cookie_and_me_returns_tenant(client, session_factory):
    reg = client.post("/api/setup", json={"email": "li@example.com", "password": "s3cret123"})
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
    resp = client.post(
        "/api/auth/login", json={"email": "ghost@example.com", "password": "s3cret123"}
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "invalid email or password"


def test_login_wrong_password_returns_401(client):
    client.post("/api/setup", json={"email": "w@example.com", "password": "right-password"})
    resp = client.post("/api/auth/login", json={"email": "w@example.com", "password": "wrong"})
    assert resp.status_code == 401
    assert "session" not in resp.headers.get("set-cookie", "")


def test_login_inactive_user_returns_401(client, session_factory):
    client.post("/api/setup", json={"email": "in@example.com", "password": "s3cret123"})
    with session_factory() as db:
        user = db.scalar(select(User).where(User.email == "in@example.com"))
        user.is_active = False
        db.commit()
    resp = client.post("/api/auth/login", json={"email": "in@example.com", "password": "s3cret123"})
    assert resp.status_code == 401
    assert "session" not in resp.headers.get("set-cookie", "")


def test_logout_deletes_session_and_clears_cookie(client):
    client.post("/api/setup", json={"email": "lo@example.com", "password": "s3cret123"})
    token = client.cookies.get("session")
    assert token is not None
    assert client.get("/api/auth/me").status_code == 200

    resp = client.post("/api/auth/logout")
    assert resp.status_code == 204
    assert client.cookies.get("session") is None
    assert client.get("/api/auth/me").status_code == 401
    assert sessions.resolve(token) is None


def test_logout_without_session_returns_204(client):
    assert client.post("/api/auth/logout").status_code == 204


def test_me_without_session_returns_401(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_deleted_user_returns_401(client, session_factory):
    client.post("/api/setup", json={"email": "nl@example.com", "password": "s3cret123"})
    with session_factory() as db:
        db.execute(User.__table__.delete())
        db.commit()
    assert client.get("/api/auth/me").status_code == 401


def test_expired_session_behaves_like_no_session(client, memory_session_store):
    client.post("/api/setup", json={"email": "ex@example.com", "password": "s3cret123"})
    assert client.get("/api/auth/me").status_code == 200
    memory_session_store.clock.advance(86400 * 30)
    assert client.get("/api/auth/me").status_code == 401
