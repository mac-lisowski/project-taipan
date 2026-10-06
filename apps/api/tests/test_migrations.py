"""Integration tests that run the real Alembic migrations on a scratch DB.

create_all never executes the migration files, so the shipped DDL (FK
cascade, unique index, types, CHECKs) is only pinned here.
"""

import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from conftest import ADMIN_URL, TEST_URL
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

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


def _assert_profiles_ddl(url):
    """Assert the DDL the migration must ship for user_profiles."""
    eng = create_engine(url)
    try:
        with eng.connect() as conn:
            condeltype = conn.execute(
                text(
                    "SELECT confdeltype FROM pg_constraint "
                    "WHERE contype = 'f' AND conrelid = 'user_profiles'::regclass"
                )
            ).scalar_one()
            assert condeltype == "c"

            unique_indexes = (
                conn.execute(
                    text(
                        "SELECT indexname FROM pg_indexes "
                        "WHERE tablename = 'user_profiles' "
                        "AND indexdef LIKE '%UNIQUE%user_id%'"
                    )
                )
                .scalars()
                .all()
            )
            assert "ix_user_profiles_user_id" in unique_indexes

            types = dict(
                conn.execute(
                    text(
                        "SELECT column_name, data_type FROM information_schema.columns "
                        "WHERE table_name = 'user_profiles' "
                        "AND column_name IN ('created_at', 'updated_at')"
                    )
                ).all()
            )
            assert types == {
                "created_at": "timestamp with time zone",
                "updated_at": "timestamp with time zone",
            }

            checks = (
                conn.execute(
                    text(
                        "SELECT conname FROM pg_constraint "
                        "WHERE contype = 'c' AND conrelid = 'user_profiles'::regclass"
                    )
                )
                .scalars()
                .all()
            )
            assert set(checks) == {
                "ck_user_profiles_display_name_len",
                "ck_user_profiles_avatar_url_len",
                "ck_user_profiles_bio_len",
            }
    finally:
        eng.dispose()


def _table_exists(url, name):
    eng = create_engine(url)
    try:
        with eng.connect() as conn:
            return (
                conn.execute(
                    text("SELECT 1 FROM information_schema.tables WHERE table_name = :name"),
                    {"name": name},
                ).scalar()
                is not None
            )
    finally:
        eng.dispose()


def test_upgrade_head_builds_expected_user_profiles_ddl(scratch_url):
    cfg = Config(str(ALEMBIC_INI))
    command.upgrade(cfg, "head")
    _assert_profiles_ddl(scratch_url)


def test_downgrade_upgrade_round_trip(scratch_url):
    cfg = Config(str(ALEMBIC_INI))
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    assert not _table_exists(scratch_url, "user_profiles")
    command.upgrade(cfg, "head")
    _assert_profiles_ddl(scratch_url)
