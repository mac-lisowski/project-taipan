from api.models import UserRole, UserTenant
from sqlalchemy import select


def test_probe_reports_setup_needed_on_empty_table(client):
    resp = client.get("/api/setup")
    assert resp.status_code == 200
    assert resp.json() == {"needs_setup": True}


def test_probe_reports_setup_done_after_user_exists(client):
    seed = client.post("/api/setup", json={"email": "u@example.com", "password": "s3cret123"})
    assert seed.status_code == 201
    assert client.get("/api/setup").json() == {"needs_setup": False}


def test_first_setup_creates_user_link_roles_and_cookie(client, session_factory):
    resp = client.post("/api/setup", json={"email": "op@example.com", "password": "s3cret123"})
    assert resp.status_code == 201
    assert resp.cookies.get("session") is not None
    user_id = resp.json()["id"]
    with session_factory() as db:
        link = db.scalar(select(UserTenant))
        assert link is not None
        assert link.user_id == user_id
        roles = sorted(db.scalars(select(UserRole.role)).all())
        assert roles == ["admin", "member"]


def test_second_setup_returns_409(client):
    first = client.post("/api/setup", json={"email": "op@example.com", "password": "s3cret123"})
    assert first.status_code == 201
    assert client.cookies.get("session") is not None
    resp = client.post("/api/setup", json={"email": "late@example.com", "password": "s3cret123"})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "setup already completed"


def test_setup_after_plain_user_exists_returns_409(client):
    first = client.post("/api/setup", json={"email": "admin@x.com", "password": "s3cret123"})
    assert first.status_code == 201
    seed = client.post("/api/users", json={"email": "u@example.com", "password": "s3cret123"})
    assert seed.status_code == 201
    resp = client.post("/api/setup", json={"email": "op@example.com", "password": "s3cret123"})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "setup already completed"


def test_setup_rejects_invalid_email_with_422(client):
    resp = client.post("/api/setup", json={"email": "not-an-email", "password": "s3cret123"})
    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_setup_rejects_empty_password_with_422(client):
    resp = client.post("/api/setup", json={"email": "op@example.com", "password": ""})
    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_register_returns_404(client):
    resp = client.post(
        "/api/auth/register", json={"email": "r@example.com", "password": "s3cret123"}
    )
    assert resp.status_code == 404
