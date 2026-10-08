"""Settings over HTTP: public read of the switch, owner-only write, pinned body shape."""

from api_testsupport import create_user, login, setup_admin


def test_fresh_db_reads_switch_false(client):
    resp = client.get("/api/system/registration")

    assert resp.status_code == 200
    assert resp.json() == {"enabled": False}


def test_owner_put_flips_switch_and_get_reads_true(client):
    setup_admin(client, "owner@x.com")

    resp = client.put("/api/system/registration", json={"enabled": True})

    assert resp.status_code == 204
    assert client.get("/api/system/registration").json() == {"enabled": True}


def test_owner_can_flip_back_off(client):
    setup_admin(client, "owner@x.com")
    assert client.put("/api/system/registration", json={"enabled": True}).status_code == 204

    resp = client.put("/api/system/registration", json={"enabled": False})

    assert resp.status_code == 204
    assert client.get("/api/system/registration").json() == {"enabled": False}


def test_anonymous_put_gets_401(client):
    resp = client.put("/api/system/registration", json={"enabled": True})

    assert resp.status_code == 401


def test_member_put_gets_403(client):
    setup_admin(client, "owner@x.com")
    create_user(client, "member@x.com")
    login(client, "member@x.com")

    resp = client.put("/api/system/registration", json={"enabled": True})

    assert resp.status_code == 403


def test_member_flip_left_switch_unchanged(client):
    setup_admin(client, "owner@x.com")
    create_user(client, "member@x.com")
    login(client, "member@x.com")
    client.put("/api/system/registration", json={"enabled": True})

    body = client.get("/api/system/registration").json()

    assert body == {"enabled": False}
