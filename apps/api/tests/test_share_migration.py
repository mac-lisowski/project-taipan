"""Real-Alembic DDL pin for the chat_thread_shares table.

create_all never runs the migration file, so cascades, the partial
unique index, and column types ship correctly only if proven against a
scratch database.
"""

from alembic import command
from alembic.config import Config
from api_testsupport import ALEMBIC_INI
from sqlalchemy import create_engine, text

PARENT_REV = "1e8aa4dfa422"


def _exists(url, table):
    eng = create_engine(url)
    try:
        with eng.connect() as conn:
            return (
                conn.execute(
                    text("SELECT 1 FROM information_schema.tables WHERE table_name = :t"),
                    {"t": table},
                ).scalar()
                is not None
            )
    finally:
        eng.dispose()


def _assert_share_ddl(url):
    """Assert the DDL the share migration must ship."""
    eng = create_engine(url)
    try:
        with eng.connect() as conn:
            on_delete = dict(
                conn.execute(
                    text(
                        "SELECT kcu.column_name, c.confdeltype FROM pg_constraint c "
                        "JOIN information_schema.key_column_usage kcu "
                        "ON kcu.constraint_name = c.conname "
                        "WHERE c.contype = 'f' "
                        "AND c.conrelid = 'chat_thread_shares'::regclass "
                        "AND kcu.table_name = 'chat_thread_shares'"
                    )
                ).all()
            )
            # Deleting the thread or the owner drops the share.
            assert on_delete == {"thread_id": "c", "created_by_user_id": "c"}

            indexdefs = dict(
                conn.execute(
                    text(
                        "SELECT indexname, indexdef FROM pg_indexes "
                        "WHERE tablename = 'chat_thread_shares'"
                    )
                ).all()
            )
            live = indexdefs["ix_chat_thread_shares_thread_live"]
            assert "UNIQUE" in live
            # One live share per thread; revoked rows keep their slot free.
            assert "revoked_at IS NULL" in live
            assert any(
                "UNIQUE" in indexdef and "token_hash" in indexdef for indexdef in indexdefs.values()
            )

            columns = dict(
                conn.execute(
                    text(
                        "SELECT column_name, data_type || '|' || is_nullable "
                        "FROM information_schema.columns "
                        "WHERE table_name = 'chat_thread_shares'"
                    )
                ).all()
            )
            assert columns == {
                "id": "uuid|NO",
                "token_hash": "text|NO",
                "thread_id": "uuid|NO",
                "tenant_id": "text|NO",
                "snapshot": "jsonb|NO",
                "title": "text|NO",
                "created_by_user_id": "integer|NO",
                "created_at": "timestamp with time zone|NO",
                "expires_at": "timestamp with time zone|YES",
                "revoked_at": "timestamp with time zone|YES",
            }
    finally:
        eng.dispose()


def test_share_migration_round_trip(scratch_url):
    cfg = Config(str(ALEMBIC_INI))
    command.upgrade(cfg, "head")
    assert _exists(scratch_url, "chat_thread_shares") is True
    _assert_share_ddl(scratch_url)
    # Pinned to the share parent: later heads must not redefine this trip.
    command.downgrade(cfg, PARENT_REV)
    assert _exists(scratch_url, "chat_thread_shares") is False
    command.upgrade(cfg, "head")
    _assert_share_ddl(scratch_url)
