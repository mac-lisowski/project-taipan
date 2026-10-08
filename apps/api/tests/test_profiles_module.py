"""Profiles module tests: real session, no HTTP.

The router mapping is pinned in test_profiles.py.
"""

import pytest
from api import users
from api.models import UserProfile
from api.users import profiles


def _create_user(session, email: str = "u@example.com"):
    user = users.register(session, email, "s3cret123")
    session.commit()
    return user


def test_get_profile_of_user_without_profile(session_factory):
    with session_factory() as db:
        user = _create_user(db, "no-prof@example.com")
        with pytest.raises(profiles.NotFound):
            profiles.get(db, user.id)


def test_get_profile_returns_user_profile(session_factory):
    with session_factory() as db:
        user = _create_user(db, "has-prof@example.com")
        created = profiles.upsert(
            db,
            user.id,
            display_name="Ada",
            avatar_url="https://x/ada.png",
            bio="coder",
        )
        db.commit()

        fetched = profiles.get(db, user.id)
        assert isinstance(fetched, UserProfile)
        assert fetched.id == created.id
        assert fetched.user_id == user.id
        assert fetched.display_name == "Ada"
        assert fetched.avatar_url == "https://x/ada.png"
        assert fetched.bio == "coder"


def test_get_profile_unknown_user_raises_users_not_found(session_factory):
    with session_factory() as db, pytest.raises(users.NotFound):
        profiles.get(db, 999999)


def test_upsert_creates_new_profile(session_factory):
    with session_factory() as db:
        user = _create_user(db, "create@example.com")
        profile = profiles.upsert(
            db,
            user.id,
            display_name="First",
            avatar_url="https://x/1.png",
            bio="initial",
        )
        assert profile.id is not None
        assert profile.user_id == user.id
        assert profile.display_name == "First"
        assert profile.avatar_url == "https://x/1.png"
        assert profile.bio == "initial"


def test_upsert_updates_existing_profile(session_factory):
    with session_factory() as db:
        user = _create_user(db, "update@example.com")
        profiles.upsert(db, user.id, display_name="Old", bio="old bio")
        db.commit()

        updated = profiles.upsert(
            db,
            user.id,
            display_name="New",
            avatar_url="https://x/new.png",
            bio="new bio",
        )
        db.commit()

        assert updated.display_name == "New"
        assert updated.avatar_url == "https://x/new.png"
        assert updated.bio == "new bio"


def test_upsert_replaces_omitted_fields_with_none(session_factory):
    with session_factory() as db:
        user = _create_user(db, "replace@example.com")
        profiles.upsert(
            db,
            user.id,
            display_name="Ada",
            avatar_url="https://x/ada.png",
            bio="long bio",
        )
        db.commit()

        # PUT semantics: omitted fields default to None and overwrite existing
        updated = profiles.upsert(db, user.id, bio="only bio")
        db.commit()

        assert updated.bio == "only bio"
        assert updated.display_name is None
        assert updated.avatar_url is None


def test_upsert_unknown_user_raises_users_not_found(session_factory):
    with session_factory() as db, pytest.raises(users.NotFound):
        profiles.upsert(db, 999999, display_name="Ghost")


def test_upsert_supports_positional_arguments(session_factory):
    with session_factory() as db:
        user = _create_user(db, "pos@example.com")
        profile = profiles.upsert(db, user.id, "Pos", "https://x/p.png", "bio")
        assert profile.display_name == "Pos"
        assert profile.avatar_url == "https://x/p.png"
        assert profile.bio == "bio"
