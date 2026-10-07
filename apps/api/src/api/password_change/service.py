"""Self-serve password change: rules over an injected session. Usable without FastAPI."""

from __future__ import annotations

from sqlalchemy.orm import Session

from api import users
from api.credentials import (
    WeakPassword,
    ensure_acceptable,
    hash_password,
    verify_password,
)
from api.models import User
from api.users import NotFound

__all__ = [
    "REVOKE_OTHER_SESSIONS",
    "NotFound",
    "SameAsOldPassword",
    "WeakPassword",
    "WrongCurrentPassword",
    "change",
]

# The one stated other-device policy. The route applies this after a good
# change and reports the outcome; False would keep other devices signed in.
REVOKE_OTHER_SESSIONS = True


class WrongCurrentPassword(Exception):
    """The submitted current password does not verify."""


class SameAsOldPassword(Exception):
    """The new password matches the current one."""


def change(session: Session, user_id: int, current_password: str, new_password: str) -> User:
    user = users.get(session, user_id)
    if not verify_password(current_password, user.hashed_password):
        raise WrongCurrentPassword()
    if verify_password(new_password, user.hashed_password):
        raise SameAsOldPassword()
    ensure_acceptable(new_password)
    user.hashed_password = hash_password(new_password)
    session.flush()
    return user
