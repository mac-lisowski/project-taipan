"""Password reset domain tests: rules over a real test session, no HTTP."""

import hashlib

import pytest
from api import password_reset, sessions, tokens, users
from api.credentials import verify_password
from api.tokens import TokenAlreadyUsed, TokenError, TokenNotFound
from email_delivery import FakeEmailSender

BASE_URL = "http://localhost:3000"
NEW = "n3w-secret-456"


def _request(db, fake, email):
    return password_reset.request(db, email=email, sender=fake, app_base_url=BASE_URL)


def _sent_token(fake):
    [mail] = fake.list_sent()
    return mail.data["link"].split("token=")[1]


def _known_user_token(db, fake, email):
    """Request a link for an existing user; return the raw token from it."""
    _request(db, fake, email)
    return _sent_token(fake)


def test_known_active_email_sends_one_link_with_hashed_token(session_factory, memory_token_store):
    fake = FakeEmailSender()
    with session_factory() as db:
        user = users.register(db, "known@x.com", "s3cret123")

        _request(db, fake, "known@x.com")

        [mail] = fake.list_sent()
        assert mail.recipient == user.email
        assert mail.data["app_name"] == password_reset.APP_NAME
        raw = _sent_token(fake)
        digest = "token:" + hashlib.sha256(raw.encode()).hexdigest()
        assert list(memory_token_store.entries) == [digest]
        assert raw not in memory_token_store.entries[digest]


def test_unknown_email_sends_nothing(session_factory):
    fake = FakeEmailSender()
    with session_factory() as db:
        result = _request(db, fake, "ghost@x.com")

    assert result is None
    assert fake.list_sent() == []


def test_inactive_email_sends_nothing(session_factory):
    fake = FakeEmailSender()
    with session_factory() as db:
        user = users.register(db, "inactive@x.com", "s3cret123")
        user.is_active = False
        db.flush()

        result = _request(db, fake, "inactive@x.com")

    assert result is None
    assert fake.list_sent() == []


def test_link_token_expires_after_configured_ttl(session_factory, memory_token_store, monkeypatch):
    fake = FakeEmailSender()
    monkeypatch.setenv("API_RESET_TOKEN_TTL_SECONDS", "60")
    with session_factory() as db:
        users.register(db, "ttl@x.com", "s3cret123")
        _known_user_token(db, fake, "ttl@x.com")

    raw = _sent_token(fake)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    assert memory_token_store.get(digest) is not None

    memory_token_store.clock.advance(61)
    assert memory_token_store.get(digest) is None
    with pytest.raises(TokenNotFound):
        tokens.verify(raw, tokens.PURPOSE_RESET)


def test_reset_with_live_token_rotates_hash_and_returns_session(session_factory):
    fake = FakeEmailSender()
    with session_factory() as db:
        user = users.register(db, "live@x.com", "s3cret123")
        raw = _known_user_token(db, fake, "live@x.com")

        session_token = password_reset.reset(db, token=raw, new_password=NEW)

        db.refresh(user)
        assert verify_password("s3cret123", user.hashed_password) is False
        assert verify_password(NEW, user.hashed_password) is True
        data = sessions.resolve(session_token)
        assert data is not None
        assert data.user_id == user.id
        with pytest.raises(TokenAlreadyUsed):
            tokens.verify(raw, tokens.PURPOSE_RESET)


def test_reset_with_expired_token_raises(session_factory, memory_token_store, monkeypatch):
    fake = FakeEmailSender()
    monkeypatch.setenv("API_RESET_TOKEN_TTL_SECONDS", "30")
    with session_factory() as db:
        users.register(db, "expired@x.com", "s3cret123")
        raw = _known_user_token(db, fake, "expired@x.com")

    memory_token_store.clock.advance(31)
    with session_factory() as db, pytest.raises(TokenNotFound):
        password_reset.reset(db, token=raw, new_password=NEW)


def test_reset_with_unknown_token_raises(session_factory):
    with session_factory() as db, pytest.raises(TokenNotFound):
        password_reset.reset(db, token="no-such-token", new_password=NEW)


def test_weak_password_rejected_and_token_stays_live(session_factory):
    fake = FakeEmailSender()
    with session_factory() as db:
        users.register(db, "weak@x.com", "s3cret123")
        raw = _known_user_token(db, fake, "weak@x.com")

        with pytest.raises(password_reset.WeakPassword):
            password_reset.reset(db, token=raw, new_password="short")

        session_token = password_reset.reset(db, token=raw, new_password=NEW)
        assert sessions.resolve(session_token) is not None


def test_reset_for_inactive_user_rejects_and_keeps_old_hash(session_factory):
    fake = FakeEmailSender()
    with session_factory() as db:
        user = users.register(db, "gated@x.com", "s3cret123")
        raw = _known_user_token(db, fake, "gated@x.com")
        user.is_active = False
        db.flush()

        with pytest.raises(TokenError):
            password_reset.reset(db, token=raw, new_password=NEW)

        db.refresh(user)
        assert verify_password("s3cret123", user.hashed_password) is True


def test_reset_revokes_prior_sessions(session_factory):
    fake = FakeEmailSender()
    with session_factory() as db:
        user = users.register(db, "sessions@x.com", "s3cret123")
        tenant_id = users.tenant_id_for_user(db, user.id)
        old_session = sessions.mint(user.id, tenant_id)
        raw = _known_user_token(db, fake, "sessions@x.com")

        new_session = password_reset.reset(db, token=raw, new_password=NEW)

        assert sessions.resolve(old_session) is None
        assert sessions.resolve(new_session).user_id == user.id
