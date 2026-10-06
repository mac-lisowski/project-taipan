import uuid
from pathlib import Path

import pytest
from api import db as db_module
from api.config import get_config
from api.db import Base
from api.main import app
from api.models.encrypted_string import set_field_crypto
from api_testsupport import KEY_ID, MapStore, StubCipher
from crypto import FieldCrypto
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

ADMIN_URL = get_config().test_admin_url
TEST_URL = get_config().test_database_url
ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


@pytest.fixture
def scratch_url(monkeypatch):
    """Unique scratch database per run; env rewired so env.py uses it."""
    try:
        admin = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
        with admin.connect():
            pass
    except OperationalError:
        pytest.skip("postgres not running (docker compose up -d)")

    dbname = f"app_test_alembic_{uuid.uuid4().hex[:10]}"
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{dbname}"'))

    url = make_url(TEST_URL).set(database=dbname).render_as_string(hide_password=False)
    # env.py imports DATABASE_URL from api.db at run time, so both must
    # point at the scratch DB before any alembic command executes.
    monkeypatch.setattr("api.db.DATABASE_URL", url)
    monkeypatch.setenv("API_DATABASE_URL", url)
    yield url
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{dbname}" WITH (FORCE)'))
    admin.dispose()


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


def create_user(client, email: str, password: str = "s3cret123") -> int:
    """Create a user through the gated route; caller holds an admin session."""
    resp = client.post("/api/users", json={"email": email, "password": password})
    assert resp.status_code == 201
    return resp.json()["id"]


def setup_admin(client, email: str = "admin@x.com", password: str = "s3cret123") -> int:
    """Run POST setup once; returns the admin user id."""
    resp = client.post("/api/setup", json={"email": email, "password": password})
    assert resp.status_code == 201
    return resp.json()["id"]


def login(client, email: str, password: str = "s3cret123") -> str:
    """Log in; returns the session cookie for manual request building."""
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 204
    token = resp.cookies.get("session")
    assert token is not None
    return token


def _stub_register():
    set_field_crypto(FieldCrypto(cipher=StubCipher(), store=MapStore(), default_key_id=KEY_ID))


@pytest.fixture
def client(engine, session_factory, monkeypatch):
    # Point the production get_db at the test factory: the boundary under
    # test is the real teardown, not a replica of it.
    monkeypatch.setattr(db_module, "SessionLocal", session_factory)
    # The lifespan runs for real; registration is stubbed, not Infisical.
    monkeypatch.setattr("api.main.build_and_register_field_crypto", _stub_register)
    with TestClient(app) as test_client:
        yield test_client
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def admin_client(client):
    """Run POST setup once; the client holds the admin session."""
    resp = client.post("/api/setup", json={"email": "admin@x.com", "password": "s3cret123"})
    assert resp.status_code == 201
    return client
