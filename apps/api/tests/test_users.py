from api.models import User
from api.security import verify_password
from sqlalchemy import select


def test_create_and_get_user(client):
    resp = client.post("/users", json={"email": "ada@example.com", "password": "s3cret"})
    assert resp.status_code == 201
    user = resp.json()
    assert user["email"] == "ada@example.com"
    assert user["is_active"] is True
    assert "password" not in user
    assert "hashed_password" not in user
    assert "created_at" in user

    resp = client.get(f"/users/{user['id']}")
    assert resp.status_code == 200


def test_list_users(client):
    client.post("/users", json={"email": "a@x.com", "password": "p"})
    client.post("/users", json={"email": "b@x.com", "password": "p"})
    resp = client.get("/users")
    assert resp.status_code == 200
    assert [u["email"] for u in resp.json()] == ["a@x.com", "b@x.com"]


def test_duplicate_email_returns_409(client):
    client.post("/users", json={"email": "dup@x.com", "password": "p"})
    resp = client.post("/users", json={"email": "dup@x.com", "password": "p"})
    assert resp.status_code == 409


def test_invalid_email_returns_422(client):
    resp = client.post("/users", json={"email": "not-an-email", "password": "p"})
    assert resp.status_code == 422


def test_get_missing_returns_404(client):
    assert client.get("/users/999").status_code == 404


def test_delete_user(client):
    user_id = client.post("/users", json={"email": "gone@x.com", "password": "p"}).json()["id"]
    assert client.delete(f"/users/{user_id}").status_code == 204
    assert client.get(f"/users/{user_id}").status_code == 404


def test_password_is_stored_hashed(client, session_factory):
    client.post("/users", json={"email": "h@x.com", "password": "plaintext"})
    with session_factory() as db:
        user = db.scalar(select(User).where(User.email == "h@x.com"))
        assert user.hashed_password != "plaintext"
        assert verify_password("plaintext", user.hashed_password)
