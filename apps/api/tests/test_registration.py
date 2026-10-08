"""Registration domain tests: switch gate, resend kill, single-use activation."""

import pytest
from api import registration, sessions, system_settings, tokens, users
from api.config import DEFAULT_APP_BASE_URL
from api.credentials import verify_password
from api.mail import APP_NAME
from api.models import User, UserTenant
from api.tokens import TokenError, TokenNotFound
from email_delivery import FakeEmailSender
from sqlalchemy import func, select

PASSWORD = "n3w-secret-456"


def _request(db, fake, email):
    return registration.request(db, email=email, sender=fake)


def _last_token(fake):
    return fake.list_sent()[-1].data["link"].split("token=")[1]


def _enable(db):
    system_settings.set_registration_enabled(db, True)


def _user_count(db, email):
    return db.scalar(select(func.count()).select_from(User).where(User.email == email))


def test_closed_switch_raises_before_any_side_effect(session_factory, memory_token_store):
    fake = FakeEmailSender()
    with session_factory() as db, pytest.raises(registration.RegistrationClosed):
        _request(db, fake, "closed@x.com")

    assert fake.list_sent() == []
    assert memory_token_store.entries == {}
    with session_factory() as db:
        assert _user_count(db, "closed@x.com") == 0


def test_open_switch_mails_one_link_and_creates_passwordless_row(session_factory):
    fake = FakeEmailSender()
    with session_factory() as db:
        _enable(db)

        _request(db, fake, "fresh@x.com")

        [mail] = fake.list_sent()
        assert mail.recipient == "fresh@x.com"
        assert mail.data["app_name"] == APP_NAME
        raw = _last_token(fake)
        assert mail.data["link"] == f"{DEFAULT_APP_BASE_URL}/register?token={raw}"
        user = users.get_by_email(db, "fresh@x.com")
        assert user is not None
        assert user.hashed_password is None
        # The personal tenant must exist or activation cannot mint a session.
        assert users.tenant_id_for_user(db, user.id) is not None
        assert (
            db.scalar(
                select(func.count()).select_from(UserTenant).where(UserTenant.user_id == user.id)
            )
            == 1
        )


def test_passwordless_row_authenticate_fails_clean(session_factory):
    fake = FakeEmailSender()
    with session_factory() as db:
        _enable(db)
        _request(db, fake, "nopw@x.com")

        assert users.authenticate(db, "nopw@x.com", "any-guess-123") is None


def test_resend_mails_again_and_kills_the_old_link(session_factory):
    fake = FakeEmailSender()
    with session_factory() as db:
        _enable(db)
        _request(db, fake, "again@x.com")
        old = _last_token(fake)

        _request(db, fake, "again@x.com")

        assert len(fake.list_sent()) == 2
        with pytest.raises(TokenError):
            tokens.verify(old, tokens.PURPOSE_ACTIVATION)
        data = tokens.verify(_last_token(fake), tokens.PURPOSE_ACTIVATION)
        assert data.user_id == users.get_by_email(db, "again@x.com").id


def test_email_with_password_gets_no_mail_and_no_new_user(session_factory):
    fake = FakeEmailSender()
    with session_factory() as db:
        users.register(db, "taken@x.com", "s3cret123")
        _enable(db)

        _request(db, fake, "taken@x.com")

        assert fake.list_sent() == []
        assert _user_count(db, "taken@x.com") == 1


def test_activation_sets_password_and_mints_session(session_factory):
    fake = FakeEmailSender()
    with session_factory() as db:
        _enable(db)
        _request(db, fake, "act@x.com")
        raw = _last_token(fake)

        session_token = registration.activate(db, token=raw, new_password=PASSWORD)

        user = users.get_by_email(db, "act@x.com")
        db.refresh(user)
        assert verify_password(PASSWORD, user.hashed_password) is True
        resolved = sessions.resolve(session_token)
        assert resolved is not None
        assert resolved.user_id == user.id
        assert users.authenticate(db, "act@x.com", "s3cret123") is None


def test_replayed_link_fails(session_factory):
    fake = FakeEmailSender()
    with session_factory() as db:
        _enable(db)
        _request(db, fake, "once@x.com")
        raw = _last_token(fake)
        registration.activate(db, token=raw, new_password=PASSWORD)

        with pytest.raises(TokenError):
            registration.activate(db, token=raw, new_password=PASSWORD)


def test_tampered_token_fails(session_factory):
    fake = FakeEmailSender()
    with session_factory() as db:
        _enable(db)
        _request(db, fake, "tamper@x.com")
        raw = _last_token(fake) + "tail"

        with pytest.raises(TokenNotFound):
            registration.activate(db, token=raw, new_password=PASSWORD)


def test_expired_link_fails(session_factory, memory_token_store, monkeypatch):
    fake = FakeEmailSender()
    monkeypatch.setenv("API_ACTIVATION_TOKEN_TTL_SECONDS", "30")
    with session_factory() as db:
        _enable(db)
        _request(db, fake, "old@x.com")
        raw = _last_token(fake)

    memory_token_store.clock.advance(31)
    with session_factory() as db, pytest.raises(TokenNotFound):
        registration.activate(db, token=raw, new_password=PASSWORD)


def test_wrong_purpose_token_fails(session_factory):
    fake = FakeEmailSender()
    with session_factory() as db:
        _enable(db)
        _request(db, fake, "mixed@x.com")
        user = users.get_by_email(db, "mixed@x.com")
        reset_raw = tokens.mint(user.id, tokens.PURPOSE_RESET, ttl_seconds=60)

        with pytest.raises(TokenError):
            registration.activate(db, token=reset_raw, new_password=PASSWORD)


def test_weak_password_rejected_and_token_stays_live(session_factory):
    fake = FakeEmailSender()
    with session_factory() as db:
        _enable(db)
        _request(db, fake, "weak@x.com")
        raw = _last_token(fake)

        with pytest.raises(registration.WeakPassword):
            registration.activate(db, token=raw, new_password="short")

        session_token = registration.activate(db, token=raw, new_password=PASSWORD)
        resolved = sessions.resolve(session_token)
        assert resolved is not None
        assert resolved.user_id == users.get_by_email(db, "weak@x.com").id


def test_deactivated_half_account_link_fails(session_factory, memory_session_store):
    fake = FakeEmailSender()
    with session_factory() as db:
        _enable(db)
        _request(db, fake, "gated@x.com")
        user = users.get_by_email(db, "gated@x.com")
        user.is_active = False
        db.flush()
        raw = _last_token(fake)

        with pytest.raises(TokenError):
            registration.activate(db, token=raw, new_password=PASSWORD)

        db.refresh(user)
        assert user.hashed_password is None
        assert memory_session_store.entries == {}


def test_activation_ignores_the_switch(session_factory):
    fake = FakeEmailSender()
    with session_factory() as db:
        _enable(db)
        _request(db, fake, "open@x.com")
        raw = _last_token(fake)
        system_settings.set_registration_enabled(db, False)
        db.flush()

        session_token = registration.activate(db, token=raw, new_password=PASSWORD)

        resolved = sessions.resolve(session_token)
        assert resolved is not None
        assert resolved.user_id == users.get_by_email(db, "open@x.com").id
