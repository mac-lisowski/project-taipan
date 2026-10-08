"""Credentials module tests: hash, policy, activation gate.

Module-level cases need no database. The users-level cases use a real
session and cover the seams registration and login route through.
"""

import pytest
from api import users
from api.credentials import (
    InactiveUser,
    WeakPassword,
    ensure_acceptable,
    ensure_active,
    hash_password,
    verify_password,
)

# Reference cases for the shared password policy: the accepted list pins
# the boundary (len >= 8), the rejected list the failures below it.
ACCEPTED_PASSWORDS = ["s3cret123", "s3cret12", "correct horse battery staple"]
REJECTED_PASSWORDS = ["", "p", "1234567"]


def test_hash_verifies_correct_password():
    hashed = hash_password("correct horse battery staple")

    assert verify_password("correct horse battery staple", hashed) is True


def test_hash_rejects_wrong_password():
    hashed = hash_password("correct horse battery staple")

    assert not verify_password("wrong horse", hashed)


@pytest.mark.parametrize("password", ACCEPTED_PASSWORDS)
def test_policy_accepts_reference_passwords(password):
    assert ensure_acceptable(password) is None


@pytest.mark.parametrize("password", REJECTED_PASSWORDS)
def test_policy_rejects_reference_passwords(password):
    with pytest.raises(WeakPassword):
        ensure_acceptable(password)


def test_gate_lets_active_user_through():
    assert ensure_active(True) is None


def test_gate_blocks_inactive_user_with_typed_error():
    with pytest.raises(InactiveUser):
        ensure_active(False)


def test_register_runs_password_policy(session_factory):
    with session_factory() as db, pytest.raises(WeakPassword):
        users.register(db, "weak@x.com", "")


def test_register_hashes_accepted_password(session_factory):
    with session_factory() as db:
        user = users.register(db, "hash@x.com", "s3cret123")

        assert user.hashed_password != "s3cret123"
        assert verify_password("s3cret123", user.hashed_password) is True


def test_authenticate_accepts_active_user(session_factory):
    with session_factory() as db:
        users.register(db, "login@x.com", "s3cret123")

        found = users.authenticate(db, "login@x.com", "s3cret123")

        assert found is not None and found.email == "login@x.com"


def test_authenticate_rejects_wrong_password(session_factory):
    with session_factory() as db:
        users.register(db, "wrong@x.com", "s3cret123")

        assert users.authenticate(db, "wrong@x.com", "nope") is None


def test_authenticate_gates_before_verify(session_factory):
    with session_factory() as db:
        user = users.register(db, "gated@x.com", "s3cret123")
        user.is_active = False
        db.commit()

        # Wrong password on purpose: if verify ran first, this returns
        # None instead of the typed gate error.
        with pytest.raises(InactiveUser):
            users.authenticate(db, "gated@x.com", "not-the-password")
