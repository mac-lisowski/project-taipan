"""Role migration tests: user_roles DDL, backfill, and later widening."""

from alembic import command
from alembic.config import Config
from conftest import ALEMBIC_INI
from sqlalchemy import create_engine, text

# The revision at which this file's user_roles DDL froze; two later
# revisions still ship the table before the head drops it.
LAST_USER_ROLES_REVISION = "c5dab48db2ae"


def _assert_roles_ddl(url):
    """Assert the DDL the migration must ship for user_roles."""
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
            assert "tenant_id" not in columns
            user_id_index = conn.execute(
                text(
                    "SELECT indexdef FROM pg_indexes "
                    "WHERE tablename = 'user_roles' AND indexname = 'ix_user_roles_user_id'"
                )
            ).scalar_one()
            assert "UNIQUE" not in user_id_index
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
    finally:
        eng.dispose()


def test_roles_backfill_grants_admin_to_earliest_user(scratch_url):
    """Users present before the roles migration: earliest gains admin."""
    cfg = Config(str(ALEMBIC_INI))
    command.upgrade(cfg, "a029aa189a91")
    eng = create_engine(scratch_url)
    with eng.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (email, hashed_password, is_active, created_at) "
                "VALUES ('later@x.com', 'h', true, now()), "
                "('earlier@x.com', 'h', true, now() - interval '1 hour')"
            )
        )
    command.upgrade(cfg, LAST_USER_ROLES_REVISION)
    with eng.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT u.email, ur.role FROM users u "
                "LEFT JOIN user_roles ur ON ur.user_id = u.id "
                "ORDER BY u.email"
            )
        ).all()
        roles_by_email: dict[str, set] = {}
        for email, role in rows:
            roles_by_email.setdefault(email, set()).add(role)
        assert roles_by_email["earlier@x.com"] == {"admin", "member"}
        assert roles_by_email["later@x.com"] == {"member"}
    eng.dispose()
    _assert_roles_ddl(scratch_url)


def test_roles_allow_member_and_multiple_roles_per_user(scratch_url):
    """The widened CHECK stores member; one user can hold two roles."""
    cfg = Config(str(ALEMBIC_INI))
    command.upgrade(cfg, LAST_USER_ROLES_REVISION)
    eng = create_engine(scratch_url)
    with eng.begin() as conn:
        uid = conn.execute(
            text(
                "INSERT INTO users (email, hashed_password, is_active) "
                "VALUES ('m@x.com', 'h', true) RETURNING id"
            )
        ).scalar_one()
        conn.execute(
            text("INSERT INTO user_roles (user_id, role) VALUES (:uid, 'member')"),
            {"uid": uid},
        )
        conn.execute(
            text("INSERT INTO user_roles (user_id, role) VALUES (:uid, 'admin')"),
            {"uid": uid},
        )
        count = conn.execute(
            text("SELECT count(*) FROM user_roles WHERE user_id = :uid"), {"uid": uid}
        ).scalar_one()
        assert count == 2
    eng.dispose()
