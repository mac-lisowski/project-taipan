"""Password change over HTTP: pinned error map, session policy, notice mail."""

from api import sessions
from api.credentials import verify_password
from api.models import User
from conftest import login
from email_delivery import FakeEmailSender
from sqlalchemy import select

NEW = "n3w-secret-456"


def _post(client, *, current="s3cret123", new=NEW, confirm=NEW):
    return client.post(
        "/api/account/password",
        json={
            "current_password": current,
            "new_password": new,
            "confirm_new_password": confirm,
        },
    )


def _register(client, email):
    resp = client.post("/api/setup", json={"email": email, "password": "s3cret123"})
    assert resp.status_code == 201


def _user_hash(session_factory, email):
    with session_factory() as db:
        user = db.scalar(select(User).where(User.email == email))
        return user.hashed_password


def test_signed_out_is_denied(client):
    resp = _post(client)

    assert resp.status_code == 401


def test_wrong_current_returns_401_and_keeps_old_hash(client, session_factory):
    _register(client, "w@x.com")

    resp = _post(client, current="not-the-password")

    assert resp.status_code == 401
    assert resp.json()["detail"] == "wrong current password"
    assert "not-the-password" not in resp.text
    assert verify_password("s3cret123", _user_hash(session_factory, "w@x.com")) is True


def test_weak_new_returns_422(client):
    _register(client, "wk@x.com")

    resp = _post(client, new="short", confirm="short")

    assert resp.status_code == 422
    assert resp.json()["detail"] == "weak password"


def test_same_as_old_returns_422(client):
    _register(client, "s@x.com")

    resp = _post(client, new="s3cret123", confirm="s3cret123")

    assert resp.status_code == 422
    assert resp.json()["detail"] == "new password matches current"


def test_mismatched_confirm_returns_422(client):
    _register(client, "m@x.com")

    resp = _post(client, confirm="different-secret")

    assert resp.status_code == 422
    assert resp.json()["detail"] == "new passwords do not match"


def test_valid_change_keeps_this_device_signed_in_and_revokes_others(client):
    _register(client, "p@x.com")
    other = login(client, "p@x.com")
    login(client, "p@x.com")

    resp = _post(client)

    assert resp.status_code == 200
    assert resp.json() == {"other_devices_signed_out": True}
    new_token = resp.cookies.get("session")
    assert new_token is not None
    fresh = sessions.resolve(new_token)
    assert fresh is not None
    assert sessions.resolve(other) is None
    me = client.get("/api/auth/me")
    assert me.status_code == 200


def test_login_after_change_requires_the_new_password(client):
    _register(client, "l@x.com")

    assert _post(client).status_code == 200
    old_login = client.post("/api/auth/login", json={"email": "l@x.com", "password": "s3cret123"})
    new_login = client.post("/api/auth/login", json={"email": "l@x.com", "password": NEW})

    assert old_login.status_code == 401
    assert new_login.status_code == 204


def test_change_sends_notice_through_shared_seam(client):
    _register(client, "n@x.com")
    fake = FakeEmailSender()
    client.app.state.email_sender = fake

    assert _post(client).status_code == 200

    [mail] = fake.list_sent()
    assert mail.template == "password_change"
    assert mail.recipient == "n@x.com"
    assert "s3cret123" not in str(mail.data)
    assert NEW not in str(mail.data)


def test_failing_notice_never_blocks_the_change(client, session_factory):
    _register(client, "f@x.com")

    class ExplodingSender:
        # Real send signature, so a drifted call contract fails here too.
        def send(self, template, recipient, data):
            raise RuntimeError("transport down")

    client.app.state.email_sender = ExplodingSender()

    resp = _post(client)

    assert resp.status_code == 200
    assert verify_password(NEW, _user_hash(session_factory, "f@x.com")) is True
