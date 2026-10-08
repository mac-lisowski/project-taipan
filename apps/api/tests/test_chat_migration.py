"""Real-Alembic DDL pin for the chat tables.

create_all never runs the migration file, so cascades, CHECKs, and
indexes ship correctly only if proven against a scratch database.
"""

from alembic import command
from alembic.config import Config
from api_testsupport import ALEMBIC_INI
from sqlalchemy import create_engine, text

CHAT_REV = "7f7c0b2d3a74"
PARENT_REV = "e7b41c903f52"


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


def _assert_chat_ddl(url):
    """Assert the DDL the chat migration must ship."""
    eng = create_engine(url)
    try:
        with eng.connect() as conn:
            on_delete = dict(
                conn.execute(
                    text(
                        "SELECT kcu.table_name, c.confdeltype FROM pg_constraint c "
                        "JOIN information_schema.key_column_usage kcu "
                        "ON kcu.constraint_name = c.conname "
                        "WHERE c.contype = 'f' AND c.conrelid IN "
                        "('chat_threads'::regclass, 'chat_messages'::regclass)"
                    )
                ).all()
            )
            # Deleting a user drops their threads; dropping a thread drops messages.
            assert on_delete["chat_threads"] == "c"
            assert on_delete["chat_messages"] == "c"

            checks = (
                conn.execute(
                    text(
                        "SELECT conname FROM pg_constraint "
                        "WHERE contype = 'c' AND conrelid IN "
                        "('chat_threads'::regclass, 'chat_messages'::regclass)"
                    )
                )
                .scalars()
                .all()
            )
            assert set(checks) >= {"ck_chat_threads_title_len", "ck_chat_messages_role"}

            indexes = (
                conn.execute(
                    text(
                        "SELECT indexname FROM pg_indexes "
                        "WHERE tablename IN ('chat_threads', 'chat_messages')"
                    )
                )
                .scalars()
                .all()
            )
            assert {"ix_chat_threads_user_created", "ix_chat_messages_thread_seq"} <= set(indexes)

            content_type = conn.execute(
                text(
                    "SELECT data_type FROM information_schema.columns "
                    "WHERE table_name = 'chat_messages' AND column_name = 'content'"
                )
            ).scalar_one()
            assert content_type == "jsonb"
    finally:
        eng.dispose()


def test_chat_migration_round_trip(scratch_url):
    cfg = Config(str(ALEMBIC_INI))
    command.upgrade(cfg, "head")
    assert _exists(scratch_url, "chat_threads")
    assert _exists(scratch_url, "chat_messages")
    _assert_chat_ddl(scratch_url)
    # Pinned to the chat parent: later heads must not redefine this trip.
    command.downgrade(cfg, PARENT_REV)
    assert not _exists(scratch_url, "chat_threads")
    assert not _exists(scratch_url, "chat_messages")
    command.upgrade(cfg, "head")
    _assert_chat_ddl(scratch_url)
