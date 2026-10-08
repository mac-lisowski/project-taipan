"""Chat storage tables: threads, their messages, and share snapshots."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db import Base

TITLE_MAX = 100

if TYPE_CHECKING:
    from api.models.user import User


class ChatThread(Base):
    """Extension table: one user's chat thread, stamped with the session tenant."""

    __tablename__ = "chat_threads"
    __table_args__ = (
        CheckConstraint(f"LENGTH(title) <= {TITLE_MAX}", name="ck_chat_threads_title_len"),
        # The list page keysets on this pair; user_id alone is covered as prefix.
        Index("ix_chat_threads_user_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    tenant_id: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship()
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="thread", cascade="all, delete-orphan", order_by="ChatMessage.seq"
    )


class ChatMessage(Base):
    """One OpenAI chat message; JSONB content keeps the wire shape verbatim."""

    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system')", name="ck_chat_messages_role"),
        Index("ix_chat_messages_thread_seq", "thread_id", "seq"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_threads.id", ondelete="CASCADE"))
    seq: Mapped[int]
    role: Mapped[str] = mapped_column(Text)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    thread: Mapped["ChatThread"] = relationship(back_populates="messages")


class ChatQueuedMessage(Base):
    """Extension table: one message queued against a thread while a run is active."""

    __tablename__ = "chat_queued_messages"
    __table_args__ = (
        # NULL->>'text' passes a bare length check, so the key must exist too.
        CheckConstraint(
            "content ? 'text' AND LENGTH(content->>'text') > 0",
            name="ck_chat_queued_messages_text",
        ),
        Index("ix_chat_queued_messages_thread_seq", "thread_id", "seq"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_threads.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    tenant_id: Mapped[str] = mapped_column(Text)
    seq: Mapped[int]
    content: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    thread: Mapped["ChatThread"] = relationship()
    user: Mapped["User"] = relationship()


class ChatThreadShare(Base):
    """Frozen thread snapshot behind a hashed token; revoked rows stay as audit.

    No ChatThread.shares relationship on purpose: an ORM cascade would
    NULL share.thread_id on thread delete instead of firing ON DELETE
    CASCADE.
    """

    __tablename__ = "chat_thread_shares"
    __table_args__ = (
        # Unique only while live; a revoked row frees the thread's slot.
        Index(
            "ix_chat_thread_shares_thread_live",
            "thread_id",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    token_hash: Mapped[str] = mapped_column(Text, unique=True)
    thread_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_threads.id", ondelete="CASCADE"))
    tenant_id: Mapped[str] = mapped_column(Text)
    snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    title: Mapped[str] = mapped_column(Text)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
