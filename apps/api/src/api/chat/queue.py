"""Queued message storage: capped, seq-ordered rows on an owned thread."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.chat.threads import NotFound, get
from api.models import ChatQueuedMessage

__all__ = [
    "QUEUE_CAP",
    "NotFound",
    "QueueFull",
    "enqueue",
    "list_for_thread",
    "remove",
    "update",
]

QUEUE_CAP = 10


class QueueFull(Exception):
    """The thread's queue already holds QUEUE_CAP rows."""


def enqueue(
    session: Session, user_id: int, tenant_id: str, thread_id: UUID, content: dict
) -> ChatQueuedMessage:
    # The owner check on the thread doubles as the 404 for foreign ids.
    get(session, user_id, thread_id)
    count = session.scalar(
        select(func.count())
        .select_from(ChatQueuedMessage)
        .where(ChatQueuedMessage.thread_id == thread_id)
    )
    if count >= QUEUE_CAP:
        raise QueueFull(thread_id)
    row = ChatQueuedMessage(
        thread_id=thread_id,
        user_id=user_id,
        # tenant_id comes from the caller's session; the flush guard rejects
        # rows that disagree with the ambient scope.
        tenant_id=tenant_id,
        seq=_next_seq(session, thread_id),
        content=content,
    )
    session.add(row)
    session.flush()
    return row


def _next_seq(session: Session, thread_id: UUID) -> int:
    # max+1 never reuses a seq, so a mid-queue delete leaves a gap on purpose.
    current = session.scalar(
        select(func.max(ChatQueuedMessage.seq)).where(ChatQueuedMessage.thread_id == thread_id)
    )
    return 0 if current is None else current + 1


def list_for_thread(session: Session, user_id: int, thread_id: UUID) -> list[ChatQueuedMessage]:
    get(session, user_id, thread_id)
    return list(
        session.scalars(
            select(ChatQueuedMessage)
            .where(ChatQueuedMessage.thread_id == thread_id)
            .order_by(ChatQueuedMessage.seq)
        ).all()
    )


def _owned_row(session: Session, user_id: int, entry_id: UUID) -> ChatQueuedMessage:
    # The user filter hides other people's rows behind a plain 404.
    row = session.get(ChatQueuedMessage, entry_id)
    if row is None or row.user_id != user_id:
        raise NotFound(entry_id)
    return row


def update(session: Session, user_id: int, entry_id: UUID, content: dict) -> ChatQueuedMessage:
    row = _owned_row(session, user_id, entry_id)
    row.content = content
    session.flush()
    return row


def remove(session: Session, user_id: int, entry_id: UUID) -> None:
    session.delete(_owned_row(session, user_id, entry_id))
    session.flush()
