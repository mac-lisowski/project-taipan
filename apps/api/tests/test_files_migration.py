"""Real-Alembic DDL pin for the files table.

create_all never runs the migration file, so RESTRICT, the CHECKs, the
partial index, and the unique constraint ship correctly only if proven
against a scratch database.
"""

import pytest
from alembic import command
from alembic.config import Config
from api_testsupport import ALEMBIC_INI
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

PARENT_REV = "706345e37b27"


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


def _assert_files_ddl(url):
    """Assert the DDL the files migration must ship."""
    eng = create_engine(url)
    try:
        with eng.connect() as conn:
            columns = dict(
                conn.execute(
                    text(
                        "SELECT column_name, data_type || '|' || is_nullable "
                        "FROM information_schema.columns WHERE table_name = 'files'"
                    )
                ).all()
            )
            assert columns == {
                "id": "uuid|NO",
                "tenant_id": "text|NO",
                "scope": "text|NO",
                "created_by_user_id": "integer|YES",
                "purpose": "text|NO",
                "bucket": "text|NO",
                "object_key": "text|NO",
                "filename": "text|NO",
                "content_type": "text|NO",
                "size_bytes": "bigint|NO",
                "sha256": "text|NO",
                "created_at": "timestamp with time zone|NO",
                "updated_at": "timestamp with time zone|NO",
            }

            # Attribution, not a delete trigger: RESTRICT ('r'), never CASCADE.
            on_delete = dict(
                conn.execute(
                    text(
                        "SELECT kcu.column_name, c.confdeltype FROM pg_constraint c "
                        "JOIN information_schema.key_column_usage kcu "
                        "ON kcu.constraint_name = c.conname "
                        "WHERE c.contype = 'f' "
                        "AND c.conrelid = 'files'::regclass "
                        "AND kcu.table_name = 'files'"
                    )
                ).all()
            )
            assert on_delete == {"created_by_user_id": "r"}

            checks = dict(
                conn.execute(
                    text(
                        "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                        "WHERE contype = 'c' AND conrelid = 'files'::regclass"
                    )
                ).all()
            )
            assert set(checks) == {
                "ck_files_scope",
                "ck_files_private_has_uploader",
                "ck_files_size_bytes",
                "ck_files_sha256_len",
            }
            assert "'tenant'::text" in checks["ck_files_private_has_uploader"]
            assert "created_by_user_id IS NOT NULL" in checks["ck_files_private_has_uploader"]

            unique = dict(
                conn.execute(
                    text(
                        "SELECT c.conname, "
                        "array_agg(kcu.column_name::text ORDER BY kcu.ordinal_position) "
                        "FROM pg_constraint c "
                        "JOIN information_schema.key_column_usage kcu "
                        "ON kcu.constraint_name = c.conname "
                        "WHERE c.contype = 'u' AND c.conrelid = 'files'::regclass "
                        "AND kcu.table_name = 'files' GROUP BY c.conname"
                    )
                ).all()
            )
            assert unique == {"uq_files_bucket_object_key": ["bucket", "object_key"]}

            indexdefs = dict(
                conn.execute(
                    text("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'files'")
                ).all()
            )
            uploader = indexdefs["ix_files_uploader_tenant_created"]
            assert "created_by_user_id, tenant_id, created_at" in uploader
            tenant = indexdefs["ix_files_tenant_created"]
            assert "tenant_id, created_at" in tenant
            # Shared listing only ever reads tenant-scope rows.
            assert "WHERE (scope = 'tenant'::text)" in tenant
    finally:
        eng.dispose()


def _assert_private_row_needs_uploader(url):
    """A private row with no uploader violates the check constraint."""
    eng = create_engine(url)
    try:
        with eng.begin() as conn:
            with pytest.raises(IntegrityError) as exc:
                conn.execute(
                    text(
                        "INSERT INTO files (tenant_id, scope, purpose, bucket, object_key, "
                        "filename, content_type, size_bytes, sha256) VALUES "
                        "('t1', 'user', 'attachment', 'b', 'k', 'f.png', 'image/png', "
                        "1, repeat('a', 64))"
                    )
                )
            assert "ck_files_private_has_uploader" in str(exc.value)
    finally:
        eng.dispose()


def test_files_migration_round_trip(scratch_url):
    cfg = Config(str(ALEMBIC_INI))
    command.upgrade(cfg, "head")
    assert _exists(scratch_url, "files") is True
    _assert_files_ddl(scratch_url)
    _assert_private_row_needs_uploader(scratch_url)
    # Pinned to the files parent: later heads must not redefine this trip.
    command.downgrade(cfg, PARENT_REV)
    assert _exists(scratch_url, "files") is False
    command.upgrade(cfg, "head")
    _assert_files_ddl(scratch_url)
