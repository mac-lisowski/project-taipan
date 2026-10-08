"""Password reset over HTTP: neutral forgot reply, pinned error map, login cookie."""

from api.models import User
from api_testsupport import create_user
from email_delivery import FakeEmailSender
from sqlalchemy import select

NEW = "n3w-secret-456"


def _register(client, email):
    resp = client.post("/api/setup", json={"email": email, "password": "s3cret123"})
    assert resp.status_code == 201


def _request_reset_token(client, email):
    """Forgot for a known email; returns the raw token from the sent link."""
    fake = FakeEmailSender()
    client.app.state.email_sender = fake
    resp = client.post("/api/auth/forgot", json={"email": email})
    assert resp.status_code == 204
    [mail] = fake.list_sent()
    return mail.data["link"].split("token=")[1]


def test_forgot_replies_identically_for_known_and_unknown(client):
    _register(client, "k@x.com")
    fake = FakeEmailSender()
    client.app.state.email_sender = fake

    known = client.post("/api/auth/forgot", json={"email": "k@x.com"})
    unknown = client.post("/api/auth/forgot", json={"email": "ghost@x.com"})

    assert known.status_code == unknown.status_code == 204
    assert known.content == b"" == unknown.content
    [mail] = fake.list_sent()
    assert mail.recipient == "k@x.com"


def test_forgot_for_inactive_user_is_neutral(client, session_factory):
    _register(client, "i@x.com")
    fake = FakeEmailSender()
    client.app.state.email_sender = fake
    with session_factory() as db:
        user = db.scalar(select(User).where(User.email == "i@x.com"))
        user.is_active = False
        # The forgot route runs in its own session; it must see this committed.
        db.commit()

    resp = client.post("/api/auth/forgot", json={"email": "i@x.com"})

    assert resp.status_code == 204
    assert resp.content == b""
    assert fake.list_sent() == []


def test_failing_send_never_breaks_the_neutral_reply(client):
    _register(client, "f@x.com")

    class ExplodingSender:
        # Real send signature, so a drifted call contract fails here too.
        def send(self, template, recipient, data):
            raise RuntimeError("transport down")

    client.app.state.email_sender = ExplodingSender()

    resp = client.post("/api/auth/forgot", json={"email": "f@x.com"})

    assert resp.status_code == 204
    assert resp.content == b""


def test_reset_with_bad_token_returns_400(client):
    resp = client.post("/api/auth/reset", json={"token": "no-such-token", "new_password": NEW})

    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid or expired reset link"


def test_reset_with_used_token_returns_400(client):
    _register(client, "u@x.com")
    token = _request_reset_token(client, "u@x.com")
    first = client.post("/api/auth/reset", json={"token": token, "new_password": NEW})
    assert first.status_code == 204

    second = client.post("/api/auth/reset", json={"token": token, "new_password": NEW})

    assert second.status_code == 400
    assert second.json()["detail"] == "invalid or expired reset link"


def test_reset_with_weak_password_returns_422(client):
    _register(client, "w@x.com")
    token = _request_reset_token(client, "w@x.com")

    resp = client.post("/api/auth/reset", json={"token": token, "new_password": "short"})

    assert resp.status_code == 422
    assert resp.json()["detail"] == "weak password"


def test_reset_with_live_token_sets_cookie_and_logs_in(client):
    _register(client, "r@x.com")
    token = _request_reset_token(client, "r@x.com")

    resp = client.post("/api/auth/reset", json={"token": token, "new_password": NEW})

    assert resp.status_code == 204
    assert resp.content == b""
    assert resp.cookies.get("session") is not None
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "r@x.com"


def test_reset_for_deleted_user_answers_invalid_link(client):
    assert (
        client.post(
            "/api/setup", json={"email": "owner@x.com", "password": "s3cret123"}
        ).status_code
        == 201
    )
    victim = create_user(client, "victim@x.com")
    token = _request_reset_token(client, "victim@x.com")
    assert client.delete(f"/api/users/{victim}").status_code == 204

    bogus = client.post("/api/auth/reset", json={"token": "no-such-token", "new_password": NEW})
    dead = client.post("/api/auth/reset", json={"token": token, "new_password": NEW})

    assert dead.status_code == bogus.status_code == 400
    assert dead.json() == bogus.json()
