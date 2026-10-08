import pytest
from api import users
from api.models import User, UserProfile
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError

# Core models carry identity and credential columns only; a feature
# column here means someone skipped the extension table.
USER_COLUMNS = {"id", "email", "hashed_password", "is_active", "created_at", "updated_at"}


def test_users_table_columns_are_locked_to_core_identity(engine):
    column_names = {col["name"] for col in inspect(engine).get_columns("users")}
    assert column_names == USER_COLUMNS


PROFILE_VALUES = {
    "display_name": "Ada Lovelace",
    "avatar_url": "https://example.com/ada.png",
    "bio": "First programmer",
}


@pytest.fixture(autouse=True)
def _clean_users(engine):
    """Profile tests assert row counts; leftover users would fake a pass."""
    yield
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM user_profiles"))
        conn.execute(text("DELETE FROM users"))


def _user_with_profile(session):
    user = User(email="ada@example.com", hashed_password="x")
    session.add(user)
    session.flush()
    session.add(UserProfile(user_id=user.id, **PROFILE_VALUES))
    session.commit()
    return user


def test_create_user_makes_no_profile(admin_client, session_factory):
    resp = admin_client.post(
        "/api/users", json={"email": "ada@example.com", "password": "s3cret123"}
    )
    assert resp.status_code == 201
    with session_factory() as session:
        profile_count = session.scalar(select(func.count()).select_from(UserProfile))
    assert profile_count == 0


def test_profile_roundtrip(session_factory):
    with session_factory() as session:
        _user_with_profile(session)
    with session_factory() as session:
        profile = session.scalar(select(UserProfile))
        assert profile.display_name == PROFILE_VALUES["display_name"]
        assert profile.avatar_url == PROFILE_VALUES["avatar_url"]
        assert profile.bio == PROFILE_VALUES["bio"]
        assert profile.user.email == "ada@example.com"


def test_profile_one_to_one(session_factory):
    with session_factory() as session:
        user = _user_with_profile(session)
        session.add(UserProfile(user_id=user.id, **PROFILE_VALUES))
        with pytest.raises(IntegrityError):
            session.commit()


def test_delete_user_cascades_profile(session_factory):
    with session_factory() as session:
        user = _user_with_profile(session)
        users.remove(session, user.id, caller_id=user.id + 1)
        # The module flushes; the caller owns the commit now.
        session.commit()
    with session_factory() as session:
        remaining = session.execute(text("SELECT count(*) FROM user_profiles")).scalar_one()
    assert remaining == 0


def test_delete_user_cascades_profile_at_db_level(session_factory, engine):
    with session_factory() as session:
        user = _user_with_profile(session)
        user_id = user.id
    # Raw SQL bypasses the ORM cascade; only the FK ON DELETE CASCADE
    # can remove the profile row here.
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
    with engine.begin() as conn:
        remaining = conn.execute(
            text("SELECT count(*) FROM user_profiles WHERE user_id = :id"), {"id": user_id}
        ).scalar_one()
    assert remaining == 0


def test_profile_requires_user(session_factory):
    with session_factory() as session:
        session.add(UserProfile(user_id=99999, **PROFILE_VALUES))
        with pytest.raises(IntegrityError):
            session.commit()
