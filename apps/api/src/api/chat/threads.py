"""Thread storage rules: titles, keyset pages, owner-scoped CRUD."""

from __future__ import annotations

import base64
import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from api.models import ChatMessage, ChatThread
from api.models.chat import TITLE_MAX

__all__ = [
    "FALLBACK_TITLE",
    "PAGE_SIZE",
    "TITLE_MAX",
    "InvalidCursor",
    "NotFound",
    "append_message",
    "create",
    "delete",
    "list_page",
    "messages",
    "rename",
    "replace_history",
]

PAGE_SIZE = 20
FALLBACK_TITLE = "New chat"


def _row(seq: int, message: dict) -> ChatMessage:
    return ChatMessage(seq=seq, role=message["role"], content=message)


class NotFound(Exception):
    """No thread with this id for the calling user."""


class InvalidCursor(Exception):
    """The opaque list cursor is unreadable."""


def create(session: Session, user_id: int, tenant_id: str, messages: list[dict]) -> ChatThread:
    thread = ChatThread(user_id=user_id, tenant_id=tenant_id, title=_derive_title(messages))
    for seq, message in enumerate(messages):
        thread.messages.append(_row(seq, message))
    session.add(thread)
    session.flush()
    return thread


def _derive_title(messages: list[dict]) -> str:
    for message in messages:
        if message["role"] != "user":
            continue
        text = _content_text(message.get("content"))
        if text:
            return text[:TITLE_MAX]
    return FALLBACK_TITLE


def _content_text(content: object) -> str:
    """First text of a message: the string itself, or its first text part."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()
    return ""


def list_page(
    session: Session, user_id: int, cursor: str | None
) -> tuple[list[ChatThread], str | None]:
    query = (
        select(ChatThread)
        .where(ChatThread.user_id == user_id)
        .order_by(ChatThread.created_at.desc(), ChatThread.id.desc())
        .limit(PAGE_SIZE)
    )
    if cursor is not None:
        query = query.where(tuple_(ChatThread.created_at, ChatThread.id) < _decode_cursor(cursor))
    page = list(session.scalars(query).all())
    has_more = len(page) == PAGE_SIZE
    return page, _encode_cursor(page[-1]) if has_more else None


def _encode_cursor(thread: ChatThread) -> str:
    payload = json.dumps({"t": thread.created_at.isoformat(), "id": str(thread.id)})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        stamp = datetime.fromisoformat(payload["t"])
        # Naive stamps compare against timestamptz via session timezone; refuse them.
        if stamp.tzinfo is None:
            raise ValueError("cursor timestamp lacks a timezone")
        return stamp, UUID(payload["id"])
    except (ValueError, KeyError, TypeError, RecursionError) as exc:
        raise InvalidCursor from exc


def get(session: Session, user_id: int, thread_id: UUID) -> ChatThread:
    # The user filter hides other people's threads behind a plain 404.
    thread = session.scalar(
        select(ChatThread).where(ChatThread.id == thread_id, ChatThread.user_id == user_id)
    )
    if thread is None:
        raise NotFound(thread_id)
    return thread


def messages(session: Session, user_id: int, thread_id: UUID) -> list[dict]:
    return [row.content for row in get(session, user_id, thread_id).messages]


def rename(session: Session, user_id: int, thread_id: UUID, title: str) -> ChatThread:
    thread = get(session, user_id, thread_id)
    thread.title = title[:TITLE_MAX]
    session.flush()
    session.refresh(thread)
    return thread


def delete(session: Session, user_id: int, thread_id: UUID) -> None:
    session.delete(get(session, user_id, thread_id))
    session.flush()


def replace_history(session: Session, thread: ChatThread, messages: list[dict]) -> None:
    # The delete flush runs first so replacement seqs never collide.
    thread.messages.clear()
    session.flush()
    for seq, message in enumerate(messages):
        thread.messages.append(_row(seq, message))
    session.flush()


def append_message(session: Session, thread: ChatThread, message: dict) -> None:
    thread.messages.append(_row(len(thread.messages), message))
    session.flush()
