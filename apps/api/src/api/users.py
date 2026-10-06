"""User rules: registration, lookup, removal. Usable without FastAPI."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models import User
from api.security import hash_password

__all__ = ["EmailTaken", "NotFound", "get", "list", "register", "remove"]


class EmailTaken(Exception):
    """Registration hit an email that already exists."""


class NotFound(Exception):
    """No user with the requested id."""


def register(session: Session, email: str, password: str) -> User:
    if session.scalar(select(User).where(User.email == email)) is not None:
        raise EmailTaken(email)
    user = User(email=email, hashed_password=hash_password(password))
    session.add(user)
    session.flush()
    session.refresh(user)
    return user


def get(session: Session, user_id: int) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise NotFound(user_id)
    return user


def list(session: Session) -> list[User]:
    # `.all()`, not `list(...)`: the name `list` is this module's function.
    return session.scalars(select(User).order_by(User.id)).all()


def remove(session: Session, user_id: int) -> None:
    session.delete(get(session, user_id))
    session.flush()
