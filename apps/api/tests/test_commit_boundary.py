"""Pins the commit boundary: only the get_db teardown commits."""

import pytest
from api.db import DbSession
from api.main import app
from api.models import User
from api.repositories import UserRepository
from api.security import verify_password
from sqlalchemy import delete, select


@pytest.fixture(autouse=True)
def _wipe_users(engine):
    """Red runs can leak rows via direct-session writes; keep tests isolated."""
    yield
    with engine.begin() as conn:
        conn.execute(delete(User))


def test_repo_add_does_not_commit(session_factory):
    with session_factory() as db:
        user = User(email="uncommitted@x.com", hashed_password="x")
        UserRepository(db).add(user)
        db.rollback()

    with session_factory() as db:
        assert db.scalar(select(User).where(User.email == "uncommitted@x.com")) is None


def test_handler_error_leaves_no_partial_row(client, session_factory):
    route_count = len(app.router.routes)

    @app.post("/api/_test-boom", status_code=201)
    def boom(db: DbSession) -> dict[str, str]:
        user = User(email="boom@x.com", hashed_password="x")
        UserRepository(db).add(user)
        raise RuntimeError("forced failure after write")

    try:
        with pytest.raises(RuntimeError, match="forced failure"):
            client.post("/api/_test-boom")
    finally:
        del app.router.routes[route_count:]

    with session_factory() as db:
        assert db.scalar(select(User).where(User.email == "boom@x.com")) is None


def test_clean_post_persists(client, session_factory):
    resp = client.post("/api/users", json={"email": "clean@x.com", "password": "p"})
    assert resp.status_code == 201

    with session_factory() as db:
        user = db.scalar(select(User).where(User.email == "clean@x.com"))
        assert user is not None
        assert verify_password("p", user.hashed_password)
