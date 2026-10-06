"""Pins the commit boundary: only the get_db teardown commits."""

import pytest
from api import users
from api.db import DbSession
from api.main import app
from api.models import User
from api.security import verify_password
from sqlalchemy import select


def test_register_does_not_commit(session_factory):
    with session_factory() as db:
        users.register(db, "uncommitted@x.com", "x")
        db.rollback()

    with session_factory() as db:
        assert db.scalar(select(User).where(User.email == "uncommitted@x.com")) is None


def test_handler_error_leaves_no_partial_row(client, session_factory):
    route_count = len(app.router.routes)

    @app.post("/api/_test-boom", status_code=201)
    def boom(db: DbSession) -> dict[str, str]:
        users.register(db, "boom@x.com", "x")
        raise RuntimeError("forced failure after write")

    try:
        with pytest.raises(RuntimeError, match="forced failure"):
            client.post("/api/_test-boom")
    finally:
        del app.router.routes[route_count:]

    with session_factory() as db:
        assert db.scalar(select(User).where(User.email == "boom@x.com")) is None


def test_clean_post_persists(admin_client, session_factory):
    resp = admin_client.post("/api/users", json={"email": "clean@x.com", "password": "p"})
    assert resp.status_code == 201

    with session_factory() as db:
        user = db.scalar(select(User).where(User.email == "clean@x.com"))
        assert user is not None
        assert verify_password("p", user.hashed_password)
