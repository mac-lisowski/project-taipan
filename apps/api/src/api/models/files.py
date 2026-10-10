"""Files extension table: object metadata and ownership, never bytes.

No ORM relationship to User on purpose. ``created_by_user_id`` is
attribution with DB-level ``ON DELETE RESTRICT``: a CASCADE would drop
rows while leaking S3 objects, and would kill tenant files with the
uploader. RESTRICT forces every user-delete path through the files
service, which owns the ordering.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base


class File(Base):
    """One stored object's metadata; bytes live in the object store."""

    __tablename__ = "files"
    __table_args__ = (
        CheckConstraint("scope IN ('user', 'tenant')", name="ck_files_scope"),
        # A private file always has an uploader; tenant files may lose theirs.
        CheckConstraint(
            "scope = 'tenant' OR created_by_user_id IS NOT NULL",
            name="ck_files_private_has_uploader",
        ),
        CheckConstraint("size_bytes >= 0", name="ck_files_size_bytes"),
        CheckConstraint("LENGTH(sha256) = 64", name="ck_files_sha256_len"),
        UniqueConstraint("bucket", "object_key", name="uq_files_bucket_object_key"),
        # Private listing keysets on this triple; the FK lookup uses the prefix.
        Index(
            "ix_files_uploader_tenant_created",
            "created_by_user_id",
            "tenant_id",
            "created_at",
        ),
        # Shared listing only ever reads tenant-scope rows.
        Index(
            "ix_files_tenant_created",
            "tenant_id",
            "created_at",
            postgresql_where=text("scope = 'tenant'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[str] = mapped_column(Text)
    scope: Mapped[str] = mapped_column(Text)
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    purpose: Mapped[str] = mapped_column(Text)
    bucket: Mapped[str] = mapped_column(Text)
    object_key: Mapped[str] = mapped_column(Text)
    filename: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
