from api.models import UserProfile
from sqlalchemy import func, select


def _create_user(client, email: str) -> int:
    resp = client.post("/api/users", json={"email": email, "password": "p"})
    assert resp.status_code == 201
    return resp.json()["id"]


def test_get_profile_of_user_without_profile(client):
    user_id = _create_user(client, "empty@x.com")
    resp = client.get(f"/api/users/{user_id}/profile")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "profile not found"}


def test_get_profile_roundtrip(client):
    user_id = _create_user(client, "round@x.com")
    payload = {"display_name": "Ada", "avatar_url": "https://x/ada.png", "bio": "hi"}
    resp = client.put(f"/api/users/{user_id}/profile", json=payload)
    assert resp.status_code == 200
    resp = client.get(f"/api/users/{user_id}/profile")
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == user_id
    assert body["display_name"] == "Ada"
    assert body["avatar_url"] == "https://x/ada.png"
    assert body["bio"] == "hi"


def test_put_upserts(client, session_factory):
    user_id = _create_user(client, "upsert@x.com")
    assert (
        client.put(f"/api/users/{user_id}/profile", json={"display_name": "one"}).status_code == 200
    )
    resp = client.put(f"/api/users/{user_id}/profile", json={"display_name": "two"})
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "two"
    with session_factory() as db:
        count = db.scalar(
            select(func.count()).select_from(UserProfile).where(UserProfile.user_id == user_id)
        )
    assert count == 1


def test_get_unknown_user_404(client):
    resp = client.get("/api/users/999/profile")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "user not found"}
    resp = client.put("/api/users/999/profile", json={"display_name": "x"})
    assert resp.status_code == 404
    assert resp.json() == {"detail": "user not found"}


def test_user_routes_unchanged(client):
    resp = client.post("/api/users", json={"email": "guard@x.com", "password": "p"})
    assert resp.status_code == 201
    user_id = resp.json()["id"]
    assert client.get(f"/api/users/{user_id}").status_code == 200
    assert client.get("/api/users").status_code == 200
    assert client.delete(f"/api/users/{user_id}").status_code == 204
    assert client.get(f"/api/users/{user_id}").status_code == 404
