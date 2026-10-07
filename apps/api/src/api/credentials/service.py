"""One home for password hashing, strength, and the activation gate.

Every flow that sets or checks a password goes through here, so the
rule can never fork between registration, reset, and change.
"""

from __future__ import annotations

from pwdlib import PasswordHash

_password_hash = PasswordHash.recommended()


def hash_password(plain: str) -> str:
    return _password_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _password_hash.verify(plain, hashed)


class WeakPassword(Exception):
    """Password fails the shared strength rule."""


class InactiveUser(Exception):
    """Login hit a user that has not been activated."""


def ensure_acceptable(password: str) -> None:
    # One shared rule for every flow that sets a password.
    if len(password) < 8:
        raise WeakPassword()


def ensure_active(is_active: bool) -> None:
    if not is_active:
        raise InactiveUser()
