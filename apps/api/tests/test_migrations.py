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


def _assert_tenancy_ddl(url):
    """Assert the DDL the migration must ship for the tenancy tables."""
    eng = create_engine(url)
    try:
        with eng.connect() as conn:
            unique_indexes = (
                conn.execute(
                    text(
                        "SELECT indexname FROM pg_indexes "
                        "WHERE tablename = 'user_tenants' "
                        "AND indexdef LIKE '%UNIQUE%user_id%'"
                    )
                )
                .scalars()
                .all()
            )
            assert "ix_user_tenants_user_id" in unique_indexes
            for table in ("tenants", "user_tenants", "sessions"):
                assert _table_exists(url, table)
            on_delete = dict(
                conn.execute(
                    text(
                        "SELECT kcu.column_name, c.confdeltype FROM pg_constraint c "
                        "JOIN information_schema.key_column_usage kcu "
                        "ON kcu.constraint_name = c.conname "
                        "WHERE c.contype = 'f' AND c.conrelid IN "
                        "('user_tenants'::regclass, 'sessions'::regclass) "
                        "AND kcu.table_name IN ('user_tenants', 'sessions')"
                    )
                ).all()
            )
            # user_id cascades on both tables; the tenant link does not.
            assert on_delete["user_id"] == "c"
            assert on_delete["tenant_id"] == "a"
            tenant_id_nullable = conn.execute(
                text(
                    "SELECT is_nullable FROM information_schema.columns "
                    "WHERE table_name = 'user_tenants' AND column_name = 'tenant_id'"
                )
            ).scalar_one()
            assert tenant_id_nullable == "NO"
    finally:
        eng.dispose()


def test_upgrade_head_builds_expected_user_profiles_ddl(scratch_url):
    cfg = Config(str(ALEMBIC_INI))
    command.upgrade(cfg, "head")
    _assert_profiles_ddl(scratch_url)


def test_tenancy_backfill_links_every_user(scratch_url):
    """Users present before the tenancy migration get a personal tenant."""
    cfg = Config(str(ALEMBIC_INI))
    command.upgrade(cfg, "7100c73337f1")
    eng = create_engine(scratch_url)
    with eng.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (email, hashed_password, is_active) "
                "VALUES ('a@x.com', 'h', true), ('b@x.com', 'h', true)"
            )
        )
    command.upgrade(cfg, "head")
    with eng.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT u.id, ut.tenant_id FROM users u "
                "JOIN user_tenants ut ON ut.user_id = u.id "
                "ORDER BY u.id"
            )
        ).all()
        assert len(rows) == 2
        assert len({r.tenant_id for r in rows}) == 2
        tenant_count = conn.execute(text("SELECT count(*) FROM tenants")).scalar_one()
        assert tenant_count == 2
    eng.dispose()
    _assert_tenancy_ddl(scratch_url)


def test_downgrade_upgrade_round_trip(scratch_url):
    cfg = Config(str(ALEMBIC_INI))
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    assert not _table_exists(scratch_url, "user_profiles")
    command.upgrade(cfg, "head")
    _assert_profiles_ddl(scratch_url)
