import pytest
from api.db import Base, get_db
from api.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

ADMIN_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
TEST_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/app_test"


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


@pytest.fixture
def client(engine, session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
