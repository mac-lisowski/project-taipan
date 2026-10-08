"""Owner activation switch over HTTP: flip, revoke, refuse."""

from api_testsupport import create_user, login, setup_admin

UNKNOWN_LOGIN = {"email": "ghost@x.com", "password": "s3cret123"}


def test_activation_flips_flag_and_returns_user(client):
    setup_admin(client, "admin@x.com")
    user_id = create_user(client, "plain@x.com")

    off = client.put(f"/api/users/{user_id}/activation", json={"active": False})

    assert off.status_code == 200
    assert off.json()["is_active"] is False
    assert off.json()["email"] == "plain@x.com"

    on = client.put(f"/api/users/{user_id}/activation", json={"active": True})

    assert on.status_code == 200
    assert on.json()["is_active"] is True


def test_activation_needs_owner(client):
    setup_admin(client, "admin@x.com")
    user_id = create_user(client, "plain@x.com")

    anonymous = client.put(
        f"/api/users/{user_id}/activation", json={"active": False}, headers={"Cookie": ""}
    )
    assert anonymous.status_code == 401

    login(client, "plain@x.com")
    member = client.put(f"/api/users/{user_id}/activation", json={"active": False})
    assert member.status_code == 403


def test_activation_unknown_user_404(client):
    setup_admin(client, "admin@x.com")
    assert client.put("/api/users/424242/activation", json={"active": False}).status_code == 404


def test_deactivation_kills_sessions_and_blocks_login(client):
    setup_admin(client, "admin@x.com")
    user_id = create_user(client, "plain@x.com")
    old_token = login(client, "plain@x.com")
    login(client, "admin@x.com")

    assert client.put(f"/api/users/{user_id}/activation", json={"active": False}).status_code == 200

    old = client.get("/api/auth/me", headers={"Cookie": f"session={old_token}"})
    assert old.status_code == 401
    # The owner's own session must survive the victim's deactivation.
    assert client.get("/api/auth/me").status_code == 200

    refused = client.post("/api/auth/login", json={"email": "plain@x.com", "password": "s3cret123"})
    unknown = client.post("/api/auth/login", json=UNKNOWN_LOGIN)
    assert refused.status_code == unknown.status_code == 401
    assert refused.json() == unknown.json()


def test_reactivation_restores_login(client):
    setup_admin(client, "admin@x.com")
    user_id = create_user(client, "plain@x.com")
    client.put(f"/api/users/{user_id}/activation", json={"active": False})
    client.put(f"/api/users/{user_id}/activation", json={"active": True})

    minted = client.post("/api/auth/login", json={"email": "plain@x.com", "password": "s3cret123"})
    assert minted.status_code == 204


def test_owner_cannot_change_own_activation(client):
    admin_id = setup_admin(client, "admin@x.com")

    resp = client.put(f"/api/users/{admin_id}/activation", json={"active": False})

    assert resp.status_code == 409
    assert resp.json()["detail"] == "cannot change your own account"


def test_inactive_user_session_rejected_even_without_revocation(client, session_factory):
    from api.models import User

    setup_admin(client, "admin@x.com")
    user_id = create_user(client, "plain@x.com")
    token = login(client, "plain@x.com")

    with session_factory() as session:
        user = session.get(User, user_id)
        user.is_active = False
        session.commit()

    resp = client.get("/api/auth/me", headers={"Cookie": f"session={token}"})
    assert resp.status_code == 401


def test_deleted_user_session_rejected_even_without_revocation(client, session_factory):
    from api.models import User

    setup_admin(client, "admin@x.com")
    user_id = create_user(client, "plain@x.com")
    token = login(client, "plain@x.com")

    # A direct row delete bypasses the revoke-all, so this pins the
    # principal row-absence path alone.
    with session_factory() as session:
        user = session.get(User, user_id)
        session.delete(user)
        session.commit()

    resp = client.get("/api/auth/me", headers={"Cookie": f"session={token}"})
    assert resp.status_code == 401
