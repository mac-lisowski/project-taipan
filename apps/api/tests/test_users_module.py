"""Users module tests: real session, no HTTP. The router mapping is pinned in test_users.py."""

import pytest
from api import users
from api.models import User
from api.security import verify_password
from sqlalchemy import delete


@pytest.fixture(autouse=True)
def _wipe_users(engine):
    """Failed tests roll back on session close; the wipe guards red runs too."""
    yield
    with engine.begin() as conn:
        conn.execute(delete(User))


def test_register_hashes_password(session_factory):
    with session_factory() as db:
        user = users.register(db, "reg@x.com", "s3cret")

        assert isinstance(user, User)
        assert user.id is not None
        assert user.hashed_password != "s3cret"
        assert verify_password("s3cret", user.hashed_password)


def test_duplicate_email_raises_email_taken(session_factory):
    with session_factory() as db:
        users.register(db, "dup@x.com", "p")

        with pytest.raises(users.EmailTaken):
            users.register(db, "dup@x.com", "p")


def test_get_returns_user(session_factory):
    with session_factory() as db:
        created = users.register(db, "get@x.com", "p")

        fetched = users.get(db, created.id)

        assert fetched.id == created.id
        assert fetched.email == "get@x.com"


def test_get_missing_raises_not_found(session_factory):
    with session_factory() as db, pytest.raises(users.NotFound):
        users.get(db, 424242)


def test_remove_deletes_user(session_factory):
    with session_factory() as db:
        user = users.register(db, "gone@x.com", "p")

        users.remove(db, user.id)

        with pytest.raises(users.NotFound):
            users.get(db, user.id)


def test_remove_missing_raises_not_found(session_factory):
    with session_factory() as db, pytest.raises(users.NotFound):
        users.remove(db, 424242)


def test_list_returns_users_by_id(session_factory):
    with session_factory() as db:
        users.register(db, "b@x.com", "p")
        users.register(db, "a@x.com", "p")

        found = users.list(db)

        assert [u.email for u in found] == ["b@x.com", "a@x.com"]
