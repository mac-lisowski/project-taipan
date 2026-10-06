"""Profile rules: lookup and upsert. Usable without FastAPI."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from api import users
from api.models import UserProfile

__all__ = ["NotFound", "get", "upsert"]


class NotFound(Exception):
    """No profile exists for the requested user id."""


def _find(session: Session, user_id: int) -> UserProfile | None:
    return session.scalar(select(UserProfile).where(UserProfile.user_id == user_id))


def get(session: Session, user_id: int) -> UserProfile:
    """Return UserProfile for user_id; raises NotFound or users.NotFound."""
    users.get(session, user_id)
    profile = _find(session, user_id)
    if profile is None:
        raise NotFound(user_id)
    return profile


def upsert(
    session: Session,
    user_id: int,
    display_name: str | None = None,
    avatar_url: str | None = None,
    bio: str | None = None,
) -> UserProfile:
    """Create or replace profile for user_id.

    Follows PUT replace semantics: omitted or None fields overwrite existing values.
    """
    user = users.get(session, user_id)
    profile = _find(session, user_id)
    if profile is None:
        profile = UserProfile(user_id=user_id)
        session.add(profile)
        user.profile = profile
    profile.display_name = display_name
    profile.avatar_url = avatar_url
    profile.bio = bio
    session.flush()
    session.refresh(profile)
    return profile
