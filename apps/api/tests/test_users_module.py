"""Users module tests: real session, no HTTP. The router mapping is pinned in test_users.py."""

import pytest
from api import users
from api.credentials import verify_password
from api.models import User


def test_register_hashes_password(session_factory):
    with session_factory() as db:
        user = users.register(db, "reg@x.com", "s3cret123")

        assert isinstance(user, User)
        assert user.id is not None
        assert user.hashed_password != "s3cret123"
        assert verify_password("s3cret123", user.hashed_password)


def test_duplicate_email_raises_email_taken(session_factory):
    with session_factory() as db:
        users.register(db, "dup@x.com", "s3cret123")

        with pytest.raises(users.EmailTaken):
            users.register(db, "dup@x.com", "s3cret123")


def test_get_returns_user(session_factory):
    with session_factory() as db:
        created = users.register(db, "get@x.com", "s3cret123")

        fetched = users.get(db, created.id)

        assert fetched.id == created.id
        assert fetched.email == "get@x.com"


def test_get_missing_raises_not_found(session_factory):
    with session_factory() as db, pytest.raises(users.NotFound):
        users.get(db, 424242)


def test_remove_deletes_user(session_factory):
    with session_factory() as db:
        user = users.register(db, "gone@x.com", "s3cret123")

        users.remove(db, user.id)

        with pytest.raises(users.NotFound):
            users.get(db, user.id)


def test_remove_missing_raises_not_found(session_factory):
    with session_factory() as db, pytest.raises(users.NotFound):
        users.remove(db, 424242)


def test_tenant_id_for_user_without_tenant_raises_not_found(session_factory):
    with session_factory() as db:
        # A user row with no tenant link; register always attaches one.
        orphan = User(email="orphan@x.com", hashed_password="not-a-hash")
        db.add(orphan)
        db.flush()

        with pytest.raises(users.NotFound):
            users.tenant_id_for_user(db, orphan.id)


def test_list_returns_users_by_id(session_factory):
    with session_factory() as db:
        users.register(db, "b@x.com", "s3cret123")
        users.register(db, "a@x.com", "s3cret123")

        found = users.list(db)

        assert [u.email for u in found] == ["b@x.com", "a@x.com"]
