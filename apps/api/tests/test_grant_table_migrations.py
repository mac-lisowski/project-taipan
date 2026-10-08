"""Grant-table migration tests: user_tenant_roles and user_system_roles.

Expand step of tenant-scoped roles: both tables plus the backfill from
user_roles, and a downgrade that removes only the new tables.
"""

import pytest
from alembic import command
from alembic.config import Config
from conftest import ALEMBIC_INI
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

# The revision just before the grant-table expansion.
PRIOR_HEAD = "e60b90cbea93"


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


def _assert_grant_table_ddl(url, table, unique_columns):
    """Assert the DDL the migration must ship for one grant table."""
    eng = create_engine(url)
    try:
        with eng.connect() as conn:
            columns = (
                conn.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns WHERE table_name = :t"
                    ),
                    {"t": table},
                )
                .scalars()
                .all()
            )
            assert sorted(columns) == sorted(["id", *unique_columns])
            fks = dict(
                conn.execute(
                    text(
                        "SELECT kcu.column_name, c.confdeltype FROM pg_constraint c "
                        "JOIN information_schema.key_column_usage kcu "
                        "ON kcu.constraint_name = c.conname "
                        f"WHERE c.contype = 'f' AND c.conrelid = '{table}'::regclass "
                        "AND kcu.table_name = :t"
                    ),
                    {"t": table},
                ).all()
            )
            # Deleting a user removes their grants; tenants own the rows otherwise.
            assert fks["user_id"] == "c"
            indexdef = conn.execute(
                text("SELECT indexdef FROM pg_indexes WHERE tablename = :t AND indexname = :ix"),
                {"t": table, "ix": f"ix_{table}_user_id"},
            ).scalar_one()
            assert "UNIQUE" not in indexdef
            unique_key = (
                conn.execute(
                    text(
                        "SELECT kcu.column_name FROM pg_constraint c "
                        "JOIN information_schema.key_column_usage kcu "
                        "ON kcu.constraint_name = c.conname "
                        f"WHERE c.contype = 'u' AND c.conrelid = '{table}'::regclass "
                        "ORDER BY kcu.ordinal_position"
                    )
                )
                .scalars()
                .all()
            )
            assert unique_key == unique_columns
            checks = (
                conn.execute(
                    text(
                        "SELECT conname FROM pg_constraint "
                        f"WHERE contype = 'c' AND conrelid = '{table}'::regclass"
                    )
                )
                .scalars()
                .all()
            )
            assert checks == [f"ck_{table}_role_allowed"]
    finally:
        eng.dispose()


def _seed_upgraded_instance(url):
    """Simulate an instance at PRIOR_HEAD: users, links, and old grants."""
    eng = create_engine(url)
    with eng.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (email, hashed_password, is_active, created_at) "
                "VALUES ('later@x.com', 'h', true, now()), "
                "('earlier@x.com', 'h', true, now() - interval '1 hour')"
            )
        )
        conn.execute(text("INSERT INTO tenants (id) VALUES ('t-earlier'), ('t-later')"))
        for email, tenant in (("earlier@x.com", "t-earlier"), ("later@x.com", "t-later")):
            conn.execute(
                text(
                    "INSERT INTO user_tenants (user_id, tenant_id) "
                    "SELECT id, :tenant FROM users WHERE email = :email"
                ),
                {"tenant": tenant, "email": email},
            )
        conn.execute(
            text(
                "INSERT INTO user_roles (user_id, role) "
                "SELECT id, 'admin' FROM users WHERE email = 'earlier@x.com'"
            )
        )
        conn.execute(text("INSERT INTO user_roles (user_id, role) SELECT id, 'member' FROM users"))
    eng.dispose()


def test_upgrade_creates_grant_tables_with_pinned_ddl(scratch_url):
    cfg = Config(str(ALEMBIC_INI))
    command.upgrade(cfg, "head")
    assert _table_exists(scratch_url, "user_tenant_roles") is True
    assert _table_exists(scratch_url, "user_system_roles") is True
    _assert_grant_table_ddl(scratch_url, "user_tenant_roles", ["user_id", "tenant_id", "role"])
    _assert_grant_table_ddl(scratch_url, "user_system_roles", ["user_id", "role"])


def test_grant_tables_enforce_role_checks_and_tenant_fk(scratch_url):
    """The CHECKs accept exactly the enum roles; tenant_id must reference tenants."""
    cfg = Config(str(ALEMBIC_INI))
    command.upgrade(cfg, "head")
    eng = create_engine(scratch_url)
    try:
        with eng.begin() as conn:
            uid = conn.execute(
                text(
                    "INSERT INTO users (email, hashed_password, is_active) "
                    "VALUES ('m@x.com', 'h', true) RETURNING id"
                )
            ).scalar_one()
            conn.execute(text("INSERT INTO tenants (id) VALUES ('t-1')"))
            conn.execute(
                text("INSERT INTO user_tenants (user_id, tenant_id) VALUES (:u, 't-1')"),
                {"u": uid},
            )
            conn.execute(
                text(
                    "INSERT INTO user_tenant_roles (user_id, tenant_id, role) "
                    "VALUES (:u, 't-1', 'member')"
                ),
                {"u": uid},
            )
            conn.execute(
                text("INSERT INTO user_system_roles (user_id, role) VALUES (:u, 'system_owner')"),
                {"u": uid},
            )
        with eng.connect() as conn:
            assert conn.execute(text("SELECT role FROM user_tenant_roles")).scalars().all() == [
                "member"
            ]
            assert conn.execute(text("SELECT role FROM user_system_roles")).scalars().all() == [
                "system_owner"
            ]
        rejected = (
            (
                "INSERT INTO user_tenant_roles (user_id, tenant_id, role) "
                "VALUES (:u, 't-1', 'owner')"
            ),
            "INSERT INTO user_system_roles (user_id, role) VALUES (:u, 'admin')",
            (
                "INSERT INTO user_tenant_roles (user_id, tenant_id, role) "
                "VALUES (:u, 't-missing', 'member')"
            ),
        )
        for sql in rejected:
            with pytest.raises(IntegrityError), eng.begin() as conn:
                conn.execute(text(sql), {"u": uid})
    finally:
        eng.dispose()


def test_upgrade_backfills_tenant_roles_and_system_owner(scratch_url):
    """Old grants become tenant roles in the linked tenant; earliest owns the system."""
    cfg = Config(str(ALEMBIC_INI))
    command.upgrade(cfg, PRIOR_HEAD)
    _seed_upgraded_instance(scratch_url)
    command.upgrade(cfg, "head")
    eng = create_engine(scratch_url)
    try:
        with eng.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT u.email, utr.tenant_id, utr.role FROM user_tenant_roles utr "
                    "JOIN users u ON u.id = utr.user_id "
                    "ORDER BY u.email, utr.role"
                )
            ).all()
            assert rows == [
                ("earlier@x.com", "t-earlier", "admin"),
                ("earlier@x.com", "t-earlier", "member"),
                ("later@x.com", "t-later", "member"),
            ]
            system_rows = conn.execute(
                text(
                    "SELECT u.email, usr.role FROM user_system_roles usr "
                    "JOIN users u ON u.id = usr.user_id"
                )
            ).all()
            assert system_rows == [("earlier@x.com", "system_owner")]
    finally:
        eng.dispose()


def test_downgrade_drops_only_the_new_tables(scratch_url):
    """Downgrade removes the new tables and keeps every prior row."""
    cfg = Config(str(ALEMBIC_INI))
    command.upgrade(cfg, PRIOR_HEAD)
    _seed_upgraded_instance(scratch_url)
    command.upgrade(cfg, "head")
    assert _table_exists(scratch_url, "user_tenant_roles") is True
    assert _table_exists(scratch_url, "user_system_roles") is True
    command.downgrade(cfg, PRIOR_HEAD)
    assert not _table_exists(scratch_url, "user_tenant_roles")
    assert not _table_exists(scratch_url, "user_system_roles")
    eng = create_engine(scratch_url)
    try:
        with eng.connect() as conn:
            grants = conn.execute(
                text(
                    "SELECT u.email, ur.role FROM user_roles ur "
                    "JOIN users u ON u.id = ur.user_id ORDER BY u.email, ur.role"
                )
            ).all()
            assert grants == [
                ("earlier@x.com", "admin"),
                ("earlier@x.com", "member"),
                ("later@x.com", "member"),
            ]
            counts = {
                name: conn.execute(text(f"SELECT count(*) FROM {name}")).scalar_one()
                for name in ("users", "tenants", "user_tenants")
            }
            assert counts == {"users": 2, "tenants": 2, "user_tenants": 2}
    finally:
        eng.dispose()
