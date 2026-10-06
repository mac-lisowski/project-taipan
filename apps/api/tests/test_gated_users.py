"""The users router needs admin; the profiles router stays open."""

NO_SESSION = {"Cookie": ""}


def _setup(client, email):
    resp = client.post("/api/setup", json={"email": email, "password": "s3cret123"})
    assert resp.status_code == 201
    return resp.json()["id"]


def _login(client, email):
    resp = client.post("/api/auth/login", json={"email": email, "password": "s3cret123"})
    assert resp.status_code == 204


def _create_plain(client, email):
    resp = client.post("/api/users", json={"email": email, "password": "s3cret123"})
    assert resp.status_code == 201
    return resp.json()["id"]


def test_list_users_needs_admin(client):
    assert client.get("/api/users").status_code == 401
    _setup(client, "admin@x.com")
    _create_plain(client, "plain@x.com")
    _login(client, "plain@x.com")
    assert client.get("/api/users").status_code == 403
    _login(client, "admin@x.com")
    resp = client.get("/api/users")
    assert resp.status_code == 200
    assert [u["email"] for u in resp.json()] == ["admin@x.com", "plain@x.com"]


def test_create_user_needs_admin(client):
    payload = {"email": "c1@x.com", "password": "s3cret123"}
    assert client.post("/api/users", json=payload).status_code == 401
    _setup(client, "admin@x.com")
    _create_plain(client, "plain@x.com")
    _login(client, "plain@x.com")
    assert client.post("/api/users", json=payload).status_code == 403
    _login(client, "admin@x.com")
    resp = client.post("/api/users", json=payload)
    assert resp.status_code == 201
    assert "session" not in resp.headers.get("set-cookie", "")
    _login(client, "c1@x.com")
    assert client.get("/api/auth/me").json()["roles"] == ["member"]


def test_get_user_needs_admin(client):
    _setup(client, "admin@x.com")
    user_id = _create_plain(client, "plain@x.com")
    assert client.get("/api/users/999", headers=NO_SESSION).status_code == 401
    _login(client, "plain@x.com")
    assert client.get(f"/api/users/{user_id}").status_code == 403
    _login(client, "admin@x.com")
    resp = client.get(f"/api/users/{user_id}")
    assert resp.status_code == 200
    assert resp.json()["email"] == "plain@x.com"


def test_delete_user_needs_admin(client):
    _setup(client, "admin@x.com")
    _create_plain(client, "plain@x.com")
    victim = _create_plain(client, "victim@x.com")
    assert client.delete(f"/api/users/{victim}", headers=NO_SESSION).status_code == 401
    _login(client, "plain@x.com")
    assert client.delete(f"/api/users/{victim}").status_code == 403
    _login(client, "admin@x.com")
    assert client.delete(f"/api/users/{victim}").status_code == 204
    assert client.get(f"/api/users/{victim}").status_code == 404


def test_profiles_stay_open_without_session(client):
    assert client.get("/api/users/999/profile", headers=NO_SESSION).status_code == 404
    admin_id = _setup(client, "admin@x.com")
    payload = {"display_name": "Op"}
    put = client.put(f"/api/users/{admin_id}/profile", json=payload, headers=NO_SESSION)
    assert put.status_code == 200
    get = client.get(f"/api/users/{admin_id}/profile", headers=NO_SESSION)
    assert get.status_code == 200
    assert get.json()["display_name"] == "Op"
