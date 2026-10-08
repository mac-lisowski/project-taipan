from api.credentials import verify_password
from api.models import User
from api_testsupport import create_user
from sqlalchemy import select


def test_create_and_get_user(admin_client):
    user_id = create_user(admin_client, "ada@example.com", "s3cret123")
    resp = admin_client.get(f"/api/users/{user_id}")
    assert resp.status_code == 200
    user = resp.json()
    assert user["email"] == "ada@example.com"
    assert user["is_active"] is True
    assert "password" not in user
    assert "hashed_password" not in user
    assert "created_at" in user


def test_list_users(admin_client):
    create_user(admin_client, "a@x.com", "s3cret123")
    create_user(admin_client, "b@x.com", "s3cret123")
    resp = admin_client.get("/api/users")
    assert resp.status_code == 200
    assert [u["email"] for u in resp.json()] == ["admin@x.com", "a@x.com", "b@x.com"]


def test_duplicate_email_returns_409(admin_client):
    admin_client.post("/api/users", json={"email": "dup@x.com", "password": "s3cret123"})
    resp = admin_client.post("/api/users", json={"email": "dup@x.com", "password": "s3cret123"})
    assert resp.status_code == 409


def test_invalid_email_returns_422(admin_client):
    resp = admin_client.post("/api/users", json={"email": "not-an-email", "password": "s3cret123"})
    assert resp.status_code == 422


def test_empty_password_returns_422(admin_client):
    resp = admin_client.post("/api/users", json={"email": "weak@x.com", "password": ""})
    assert resp.status_code == 422


def test_get_missing_returns_404(admin_client):
    assert admin_client.get("/api/users/999").status_code == 404


def test_delete_missing_returns_404(admin_client):
    assert admin_client.delete("/api/users/999").status_code == 404


def test_delete_user(admin_client):
    user_id = create_user(admin_client, "gone@x.com", "s3cret123")
    assert admin_client.delete(f"/api/users/{user_id}").status_code == 204
    assert admin_client.get(f"/api/users/{user_id}").status_code == 404


def test_password_is_stored_hashed(admin_client, session_factory):
    create_user(admin_client, "h@x.com", "plaintext")
    with session_factory() as db:
        user = db.scalar(select(User).where(User.email == "h@x.com"))
        assert user.hashed_password != "plaintext"
        assert verify_password("plaintext", user.hashed_password) is True
