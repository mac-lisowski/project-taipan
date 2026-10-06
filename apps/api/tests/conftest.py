import os

import pytest
from api import db as db_module
from api.db import Base
from api.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

ADMIN_URL = os.environ.get(
    "API_TEST_ADMIN_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/postgres",
)
TEST_URL = os.environ.get(
    "API_TEST_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/app_test",
)


@pytest.fixture(scope="session")
def engine():
    """One `app_test` database per test run, recreated clean."""
    try:
        admin = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
        with admin.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = 'app_test'")
            ).scalar()
            if not exists:
                conn.execute(text("CREATE DATABASE app_test"))
        admin.dispose()
    except OperationalError:
        pytest.skip("postgres not running (docker compose up -d)")

    eng = create_engine(TEST_URL)
    with eng.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
def wipe_users(engine):
    """User-row hygiene for every test; guards red runs that leave rows."""
    yield
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM users"))


@pytest.fixture
def client(engine, session_factory, monkeypatch):
    # Point the production get_db at the test factory: the boundary under
    # test is the real teardown, not a replica of it.
    monkeypatch.setattr(db_module, "SessionLocal", session_factory)
    yield TestClient(app)
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
