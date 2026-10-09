"""Registration over HTTP: closed door 404, one neutral answer, activation cookie."""

from api import system_settings, tokens
from api.models import User
from email_delivery import FakeEmailSender
from sqlalchemy import func, select

PASSWORD = "n3w-secret-456"
DETAIL = "invalid or expired activation link"


def _enable(session_factory, enabled=True):
    with session_factory() as db:
        system_settings.set_registration_enabled(db, enabled)
        db.commit()


def _register(client, email):
    return client.post("/api/auth/register", json={"email": email})


def _activate(client, token, password=PASSWORD):
    return client.post("/api/auth/activate", json={"token": token, "password": password})


def _pin_fake(client):
    fake = FakeEmailSender()
    client.app.state.email_sender = fake
    return fake


def _sent_token(fake):
    return fake.list_sent()[-1].data["link"].split("token=")[1]


def test_default_off_answers_404_with_zero_side_effects(
    client, session_factory, memory_token_store
):
    fake = _pin_fake(client)

    resp = _register(client, "door@x.com")

    assert resp.status_code == 404
    assert fake.list_sent() == []
    assert memory_token_store.entries == {}
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 0


def test_switch_off_answers_404_for_known_caller_too(client, memory_token_store):
    resp = client.post("/api/setup", json={"email": "owner@x.com", "password": "s3cret123"})
    assert resp.status_code == 201
    fake = _pin_fake(client)

    known = _register(client, "owner@x.com")
    unknown = _register(client, "ghost@x.com")

    assert known.status_code == unknown.status_code == 404
    assert known.content == unknown.content
    assert fake.list_sent() == []
    assert memory_token_store.entries == {}


def test_open_switch_sends_exactly_one_mail_with_raw_token(client, session_factory):
    _enable(session_factory)
    fake = _pin_fake(client)

    resp = _register(client, "fresh@x.com")

    assert resp.status_code == 204
    assert resp.content == b""
    [mail] = fake.list_sent()
    assert mail.recipient == "fresh@x.com"
    raw = _sent_token(fake)
    assert raw and mail.data["link"].endswith(f"register?token={raw}")


def test_known_and_unknown_emails_answer_alike(client, session_factory):
    _enable(session_factory)
    resp = client.post("/api/setup", json={"email": "owner@x.com", "password": "s3cret123"})
    assert resp.status_code == 201
    fake = _pin_fake(client)

    known = _register(client, "owner@x.com")
    unknown = _register(client, "ghost@x.com")

    assert known.status_code == unknown.status_code == 204
    assert known.content == unknown.content == b""
    [mail] = fake.list_sent()
    assert mail.recipient == "ghost@x.com"


def test_resend_mails_again_and_old_link_dies(client, session_factory):
    _enable(session_factory)
    fake = _pin_fake(client)
    _register(client, "twice@x.com")
    old = _sent_token(fake)

    _register(client, "twice@x.com")

    assert len(fake.list_sent()) == 2
    replay = _activate(client, old)
    assert replay.status_code == 400
    assert replay.json()["detail"] == DETAIL
    assert _activate(client, _sent_token(fake)).status_code == 204


def test_activation_sets_cookie_and_login_works(client, session_factory):
    _enable(session_factory)
    fake = _pin_fake(client)
    _register(client, "act@x.com")

    resp = _activate(client, _sent_token(fake))

    assert resp.status_code == 204
    assert resp.cookies.get("session") is not None
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "act@x.com"
    login = client.post("/api/auth/login", json={"email": "act@x.com", "password": PASSWORD})
    assert login.status_code == 204


def test_replay_fails(client, session_factory):
    _enable(session_factory)
    fake = _pin_fake(client)
    _register(client, "once@x.com")
    raw = _sent_token(fake)
    assert _activate(client, raw).status_code == 204

    resp = _activate(client, raw)

    assert resp.status_code == 400
    assert resp.json()["detail"] == DETAIL


def test_tampered_token_fails(client, session_factory):
    _enable(session_factory)
    fake = _pin_fake(client)
    _register(client, "tamper@x.com")

    resp = _activate(client, _sent_token(fake) + "tail")

    assert resp.status_code == 400
    assert resp.json()["detail"] == DETAIL


def test_expired_token_fails(client, session_factory, memory_token_store, monkeypatch):
    monkeypatch.setenv("API_ACTIVATION_TOKEN_TTL_SECONDS", "30")
    _enable(session_factory)
    fake = _pin_fake(client)
    _register(client, "old@x.com")
    raw = _sent_token(fake)

    memory_token_store.clock.advance(31)
    resp = _activate(client, raw)

    assert resp.status_code == 400
    assert resp.json()["detail"] == DETAIL


def test_wrong_purpose_token_fails(client, session_factory):
    _enable(session_factory)
    _register(client, "mixed@x.com")
    with session_factory() as db:
        user_id = db.scalar(select(User.id).where(User.email == "mixed@x.com"))
    reset_raw = tokens.mint(user_id, tokens.PURPOSE_RESET, ttl_seconds=60)

    resp = _activate(client, reset_raw)

    assert resp.status_code == 400
    assert resp.json()["detail"] == DETAIL


def test_weak_password_422_and_token_still_usable(client, session_factory):
    _enable(session_factory)
    fake = _pin_fake(client)
    _register(client, "weak@x.com")
    raw = _sent_token(fake)

    weak = _activate(client, raw, password="short")
    good = _activate(client, raw)

    assert weak.status_code == 422
    assert weak.json()["detail"] == "weak password"
    assert good.status_code == 204


def test_deactivated_half_account_link_fails(client, session_factory):
    _enable(session_factory)
    fake = _pin_fake(client)
    _register(client, "half@x.com")
    raw = _sent_token(fake)
    with session_factory() as db:
        user = db.scalar(select(User).where(User.email == "half@x.com"))
        user.is_active = False
        db.commit()

    resp = _activate(client, raw)

    assert resp.status_code == 400
    assert resp.json()["detail"] == DETAIL
    assert "session" not in resp.cookies
    with session_factory() as db:
        user = db.scalar(select(User).where(User.email == "half@x.com"))
        assert user.hashed_password is None


def test_link_from_open_period_activates_after_switch_closes(client, session_factory):
    _enable(session_factory)
    fake = _pin_fake(client)
    _register(client, "open@x.com")
    raw = _sent_token(fake)
    _enable(session_factory, enabled=False)

    resp = _activate(client, raw)

    assert resp.status_code == 204


def test_passwordless_login_fails_cleanly(client, session_factory):
    _enable(session_factory)
    _register(client, "nopw@x.com")

    resp = client.post("/api/auth/login", json={"email": "nopw@x.com", "password": "any-guess-123"})

    assert resp.status_code == 401


def test_register_works_after_owner_flips_switch_over_http(client):
    resp = client.post("/api/setup", json={"email": "owner@x.com", "password": "s3cret123"})
    assert resp.status_code == 201
    flip = client.put("/api/system/registration", json={"enabled": True})
    assert flip.status_code == 204
    fake = _pin_fake(client)

    resp = _register(client, "late@x.com")

    assert resp.status_code == 204
    [mail] = fake.list_sent()
    assert mail.recipient == "late@x.com"


def test_activate_for_deleted_user_answers_invalid_link(
    client, session_factory, memory_token_store
):
    assert (
        client.post(
            "/api/setup", json={"email": "owner@x.com", "password": "s3cret123"}
        ).status_code
        == 201
    )
    _enable(session_factory)
    fake = _pin_fake(client)
    assert _register(client, "gone@x.com").status_code == 204
    token = _sent_token(fake)
    gone_id = next(
        u["id"] for u in client.get("/api/users").json()["items"] if u["email"] == "gone@x.com"
    )
    assert client.delete(f"/api/users/{gone_id}").status_code == 204

    bogus = _activate(client, "not-a-token")
    dead = _activate(client, token)

    assert dead.status_code == bogus.status_code == 400
    assert dead.json() == bogus.json()
