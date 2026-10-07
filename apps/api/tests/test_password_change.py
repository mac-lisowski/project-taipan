"""Password change domain tests: rules over a real test session, no HTTP."""

import pytest
from api import password_change, users
from api.credentials import verify_password
from api.users import NotFound


def test_change_with_wrong_current_fails(session_factory):
    with session_factory() as db:
        user = users.register(db, "wrong-current@x.com", "s3cret123")

        with pytest.raises(password_change.WrongCurrentPassword):
            password_change.change(db, user.id, "not-the-password", "n3w-secret-456")

        db.refresh(user)
        assert verify_password("s3cret123", user.hashed_password) is True


def test_change_with_weak_new_fails(session_factory):
    with session_factory() as db:
        user = users.register(db, "weak-new@x.com", "s3cret123")

        with pytest.raises(password_change.WeakPassword):
            password_change.change(db, user.id, "s3cret123", "short")

        db.refresh(user)
        assert verify_password("s3cret123", user.hashed_password) is True


def test_change_with_same_as_old_fails(session_factory):
    with session_factory() as db:
        user = users.register(db, "same-as-old@x.com", "s3cret123")

        with pytest.raises(password_change.SameAsOldPassword):
            password_change.change(db, user.id, "s3cret123", "s3cret123")


def test_valid_change_stores_new_hash(session_factory):
    with session_factory() as db:
        user = users.register(db, "valid-change@x.com", "s3cret123")

        password_change.change(db, user.id, "s3cret123", "n3w-secret-456")

        db.refresh(user)
        assert verify_password("s3cret123", user.hashed_password) is False
        assert verify_password("n3w-secret-456", user.hashed_password) is True


def test_change_for_unknown_user_raises_not_found(session_factory):
    with session_factory() as db, pytest.raises(NotFound):
        password_change.change(db, 999999, "s3cret123", "n3w-secret-456")


def test_change_flushes_without_committing(session_factory):
    with session_factory() as db:
        user = users.register(db, "uncommitted@x.com", "s3cret123")
        db.commit()
        password_change.change(db, user.id, "s3cret123", "n3w-secret-456")
        db.rollback()

    with session_factory() as db:
        found = users.authenticate(db, "uncommitted@x.com", "s3cret123")

        assert found is not None
