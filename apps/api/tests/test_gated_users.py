"""The users router needs the system owner; profiles need a session and stay self only."""

from api_testsupport import create_user, grant_tenant_admin, login, setup_admin

NO_SESSION = {"Cookie": ""}


def test_list_users_needs_admin(client):
    assert client.get("/api/users").status_code == 401
    setup_admin(client, "admin@x.com")
    create_user(client, "plain@x.com")
    login(client, "plain@x.com")
    assert client.get("/api/users").status_code == 403
    login(client, "admin@x.com")
    resp = client.get("/api/users")
    assert resp.status_code == 200
    assert [u["email"] for u in resp.json()] == ["admin@x.com", "plain@x.com"]


def test_create_user_needs_admin(client):
    payload = {"email": "c1@x.com", "password": "s3cret123"}
    assert client.post("/api/users", json=payload).status_code == 401
    setup_admin(client, "admin@x.com")
    create_user(client, "plain@x.com")
    login(client, "plain@x.com")
    assert client.post("/api/users", json=payload).status_code == 403
    login(client, "admin@x.com")
    resp = client.post("/api/users", json=payload)
    assert resp.status_code == 201
    assert "session" not in resp.headers.get("set-cookie", "")
    login(client, "c1@x.com")
    assert client.get("/api/auth/me").json()["roles"] == ["member"]


def test_get_user_needs_admin(client):
    setup_admin(client, "admin@x.com")
    user_id = create_user(client, "plain@x.com")
    assert client.get("/api/users/999", headers=NO_SESSION).status_code == 401
    login(client, "plain@x.com")
    assert client.get(f"/api/users/{user_id}").status_code == 403
    login(client, "admin@x.com")
    resp = client.get(f"/api/users/{user_id}")
    assert resp.status_code == 200
    assert resp.json()["email"] == "plain@x.com"


def test_delete_user_needs_admin(client):
    setup_admin(client, "admin@x.com")
    create_user(client, "plain@x.com")
    victim = create_user(client, "victim@x.com")
    assert client.delete(f"/api/users/{victim}", headers=NO_SESSION).status_code == 401
    login(client, "plain@x.com")
    assert client.delete(f"/api/users/{victim}").status_code == 403
    login(client, "admin@x.com")
    assert client.delete(f"/api/users/{victim}").status_code == 204
    assert client.get(f"/api/users/{victim}").status_code == 404


def test_profiles_need_session_and_stay_self_only(client):
    admin_id = setup_admin(client, "admin@x.com")
    other = create_user(client, "other@x.com")

    assert client.get(f"/api/users/{other}/profile", headers=NO_SESSION).status_code == 401
    put_anon = client.put(
        f"/api/users/{other}/profile", json={"display_name": "X"}, headers=NO_SESSION
    )
    assert put_anon.status_code == 401

    login(client, "other@x.com")
    assert client.get(f"/api/users/{admin_id}/profile").status_code == 403
    assert (
        client.put(f"/api/users/{admin_id}/profile", json={"display_name": "X"}).status_code == 403
    )
    assert client.get(f"/api/users/{other}/profile").status_code == 404
    assert (
        client.put(f"/api/users/{other}/profile", json={"display_name": "Other"}).status_code == 200
    )
    assert client.get(f"/api/users/{other}/profile").json()["display_name"] == "Other"


def test_users_routes_reject_tenant_admin_without_owner(client, session_factory):
    setup_admin(client, "admin@x.com")
    aider = create_user(client, "aider@x.com")
    grant_tenant_admin(session_factory, aider)
    login(client, "aider@x.com")

    assert client.get("/api/users").status_code == 403
    payload = {"email": "new@x.com", "password": "s3cret123"}
    assert client.post("/api/users", json=payload).status_code == 403
    assert client.get("/api/users/999").status_code == 403
    assert client.delete("/api/users/999").status_code == 403
    put = client.put("/api/users/999/activation", json={"active": False})
    assert put.status_code == 403
