from datetime import datetime

from api.models import UserProfile
from api_testsupport import create_user, login
from sqlalchemy import func, select


def _assert_tz_aware(body, key):
    # now() makes the column non-null, and the timestamptz column must
    # round trip as an offset-bearing timestamp.
    assert datetime.fromisoformat(body[key]).tzinfo is not None


def _create_user(client, email: str) -> int:
    if client.get("/api/setup").json()["needs_setup"]:
        setup = client.post("/api/setup", json={"email": "admin@x.com", "password": "s3cret123"})
        assert setup.status_code == 201
    return create_user(client, email, "s3cret123")


def test_get_profile_of_user_without_profile(client):
    user_id = _create_user(client, "empty@x.com")
    login(client, "empty@x.com")
    resp = client.get(f"/api/users/{user_id}/profile")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "profile not found"}


def test_get_profile_roundtrip(client):
    user_id = _create_user(client, "round@x.com")
    login(client, "round@x.com")
    payload = {"display_name": "Ada", "avatar_url": "https://x/ada.png", "bio": "hi"}
    resp = client.put(f"/api/users/{user_id}/profile", json=payload)
    assert resp.status_code == 200
    _assert_tz_aware(resp.json(), "created_at")
    _assert_tz_aware(resp.json(), "updated_at")
    resp = client.get(f"/api/users/{user_id}/profile")
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == user_id
    assert body["display_name"] == "Ada"
    assert body["avatar_url"] == "https://x/ada.png"
    assert body["bio"] == "hi"
    _assert_tz_aware(body, "created_at")
    _assert_tz_aware(body, "updated_at")


def test_put_upserts(client, session_factory):
    user_id = _create_user(client, "upsert@x.com")
    login(client, "upsert@x.com")
    assert (
        client.put(f"/api/users/{user_id}/profile", json={"display_name": "one"}).status_code == 200
    )
    resp = client.put(f"/api/users/{user_id}/profile", json={"display_name": "two"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["display_name"] == "two"
    _assert_tz_aware(body, "created_at")
    _assert_tz_aware(body, "updated_at")
    with session_factory() as db:
        count = db.scalar(
            select(func.count()).select_from(UserProfile).where(UserProfile.user_id == user_id)
        )
    assert count == 1


def test_put_replaces_omitted_fields_with_null(client):
    user_id = _create_user(client, "replace@x.com")
    login(client, "replace@x.com")
    full = {"display_name": "Ada", "avatar_url": "https://x/ada.png", "bio": "hi"}
    assert client.put(f"/api/users/{user_id}/profile", json=full).status_code == 200
    resp = client.put(f"/api/users/{user_id}/profile", json={"bio": "updated"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["bio"] == "updated"
    assert body["display_name"] is None
    assert body["avatar_url"] is None


def test_put_rejects_oversize_bio(client):
    user_id = _create_user(client, "toolong@x.com")
    resp = client.put(f"/api/users/{user_id}/profile", json={"bio": "x" * 5001})
    assert resp.status_code == 422


def test_profile_of_unknown_user_needs_session_first(client):
    assert client.get("/api/users/999/profile").status_code == 401


def test_profile_of_unknown_user_is_hidden_behind_self_rule(client):
    _create_user(client, "anon@x.com")
    login(client, "anon@x.com")
    resp = client.get("/api/users/999/profile")
    assert resp.status_code == 403
    resp = client.put("/api/users/999/profile", json={"display_name": "x"})
    assert resp.status_code == 403


def test_user_routes_work_for_admin(client):
    setup = client.post("/api/setup", json={"email": "admin@x.com", "password": "s3cret123"})
    assert setup.status_code == 201
    resp = client.post("/api/users", json={"email": "guard@x.com", "password": "s3cret123"})
    assert resp.status_code == 201
    user_id = resp.json()["id"]
    assert client.get(f"/api/users/{user_id}").status_code == 200
    assert client.get("/api/users").status_code == 200
    assert client.delete(f"/api/users/{user_id}").status_code == 204
    assert client.get(f"/api/users/{user_id}").status_code == 404
