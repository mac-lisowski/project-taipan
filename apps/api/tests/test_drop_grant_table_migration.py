"""Old-grant-table contract tests: user_roles drops, downgrade copies back.

Contract step of tenant-scoped roles: upgrading removes user_roles and
keeps both new tables; downgrading recreates it with the original DDL
and the user and role pairs copied back from user_tenant_roles.
"""

from alembic import command
from alembic.config import Config
from conftest import ALEMBIC_INI
from sqlalchemy import create_engine, text

# The last revision that still ships the old grant table.
LAST_REVISION_WITH_USER_ROLES = "f57a78ef14d6"


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


def _assert_recreated_user_roles_ddl(url):
    """Assert the downgrade rebuilds the exact pre-drop user_roles DDL."""
    eng = create_engine(url)
    try:
        with eng.connect() as conn:
            columns = (
                conn.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = 'user_roles'"
                    )
                )
                .scalars()
                .all()
            )
            assert sorted(columns) == ["id", "role", "user_id"]
            confdeltype = conn.execute(
                text(
                    "SELECT confdeltype FROM pg_constraint "
                    "WHERE contype = 'f' AND conrelid = 'user_roles'::regclass"
                )
            ).scalar_one()
            assert confdeltype == "c"
            unique_key = (
                conn.execute(
                    text(
                        "SELECT kcu.column_name FROM pg_constraint c "
                        "JOIN information_schema.key_column_usage kcu "
                        "ON kcu.constraint_name = c.conname "
                        "WHERE c.contype = 'u' AND c.conrelid = 'user_roles'::regclass "
                        "ORDER BY kcu.ordinal_position"
                    )
                )
                .scalars()
                .all()
            )
            assert unique_key == ["user_id", "role"]
            checks = (
                conn.execute(
                    text(
                        "SELECT conname FROM pg_constraint "
                        "WHERE contype = 'c' AND conrelid = 'user_roles'::regclass"
                    )
                )
                .scalars()
                .all()
            )
            assert checks == ["ck_user_roles_role_allowed"]
            indexdef = conn.execute(
                text(
                    "SELECT indexdef FROM pg_indexes "
                    "WHERE tablename = 'user_roles' AND indexname = 'ix_user_roles_user_id'"
                )
            ).scalar_one()
            assert "UNIQUE" not in indexdef
    finally:
        eng.dispose()


def test_upgrade_drops_the_old_grant_table(scratch_url):
    """The old grant table is gone after the upgrade; both new tables remain."""
    cfg = Config(str(ALEMBIC_INI))
    command.upgrade(cfg, "head")
    assert not _table_exists(scratch_url, "user_roles")
    assert _table_exists(scratch_url, "user_tenant_roles") is True
    assert _table_exists(scratch_url, "user_system_roles") is True


def test_downgrade_recreates_old_table_with_grants_copied_back(scratch_url):
    """Downgrade rebuilds the old table and copies the tenant grants into it."""
    cfg = Config(str(ALEMBIC_INI))
    command.upgrade(cfg, "head")
    eng = create_engine(scratch_url)
    try:
        with eng.begin() as conn:
            uid = conn.execute(
                text(
                    "INSERT INTO users (email, hashed_password, is_active) "
                    "VALUES ('down@x.com', 'h', true) RETURNING id"
                )
            ).scalar_one()
            conn.execute(text("INSERT INTO tenants (id) VALUES ('t-down')"))
            conn.execute(
                text("INSERT INTO user_tenants (user_id, tenant_id) VALUES (:u, 't-down')"),
                {"u": uid},
            )
            conn.execute(
                text(
                    "INSERT INTO user_tenant_roles (user_id, tenant_id, role) "
                    "VALUES (:u, 't-down', 'admin'), (:u, 't-down', 'member')"
                ),
                {"u": uid},
            )
    finally:
        eng.dispose()
    command.downgrade(cfg, LAST_REVISION_WITH_USER_ROLES)
    assert _table_exists(scratch_url, "user_roles") is True
    assert _table_exists(scratch_url, "user_tenant_roles") is True
    _assert_recreated_user_roles_ddl(scratch_url)
    eng = create_engine(scratch_url)
    try:
        with eng.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT u.email, ur.role FROM user_roles ur "
                    "JOIN users u ON u.id = ur.user_id ORDER BY u.email, ur.role"
                )
            ).all()
            assert rows == [("down@x.com", "admin"), ("down@x.com", "member")]
    finally:
        eng.dispose()
