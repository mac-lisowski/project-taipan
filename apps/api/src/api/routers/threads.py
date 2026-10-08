"""Thin chat thread routes: storage and share endpoints, session scoped."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from api import chat
from api.authz import Principal, current_principal
from api.db import DbSession
from api.models import ChatQueuedMessage, ChatThread
from api.schemas import (
    QueueCreate,
    QueueRead,
    QueueUpdate,
    ShareCreateRead,
    ShareStatusRead,
    ThreadCreate,
    ThreadListRead,
    ThreadRead,
    ThreadUpdate,
)

PrincipalSession = Annotated[Principal, Depends(current_principal)]

router = APIRouter(prefix="/threads", tags=["chat"])


def _thread_out(thread: ChatThread) -> ThreadRead:
    return ThreadRead(
        id=str(thread.id), title=thread.title, created_at=thread.created_at.timestamp()
    )


def _queue_out(row: ChatQueuedMessage) -> QueueRead:
    return QueueRead(
        id=str(row.id),
        thread_id=str(row.thread_id),
        seq=row.seq,
        content=row.content,
        created_at=row.created_at.timestamp(),
    )


@router.get("/get", response_model=ThreadListRead, response_model_exclude_none=True)
def get_threads(
    db: DbSession,
    principal: PrincipalSession,
    cursor: str | None = None,
) -> ThreadListRead:
    try:
        page, next_cursor = chat.threads.list_page(db, principal.user_id, cursor)
    except chat.threads.InvalidCursor as exc:
        raise HTTPException(status_code=400, detail="invalid cursor") from exc
    return ThreadListRead(threads=[_thread_out(thread) for thread in page], next_cursor=next_cursor)


@router.post("/create", response_model=ThreadRead)
def create_thread(payload: ThreadCreate, db: DbSession, principal: PrincipalSession) -> ThreadRead:
    stored = [message.model_dump() for message in payload.messages]
    # The create write gets the same history caps as the completion path.
    try:
        chat.complete.validate(stored)
    except chat.complete.MessageCapError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    thread = chat.threads.create(db, principal.user_id, principal.tenant_id, stored)
    return _thread_out(thread)


@router.get("/get/{thread_id}", response_model=list[dict])
def get_thread_messages(thread_id: UUID, db: DbSession, principal: PrincipalSession) -> list[dict]:
    try:
        return chat.threads.messages(db, principal.user_id, thread_id)
    except chat.threads.NotFound as exc:
        raise HTTPException(status_code=404, detail="thread not found") from exc


@router.patch("/update/{thread_id}", response_model=ThreadRead)
def update_thread(
    thread_id: UUID, payload: ThreadUpdate, db: DbSession, principal: PrincipalSession
) -> ThreadRead:
    try:
        thread = chat.threads.rename(db, principal.user_id, thread_id, payload.title)
    except chat.threads.NotFound as exc:
        raise HTTPException(status_code=404, detail="thread not found") from exc
    return _thread_out(thread)


@router.delete("/delete/{thread_id}", status_code=204)
def delete_thread(thread_id: UUID, db: DbSession, principal: PrincipalSession) -> None:
    try:
        chat.threads.delete(db, principal.user_id, thread_id)
    except chat.threads.NotFound as exc:
        raise HTTPException(status_code=404, detail="thread not found") from exc


@router.post("/queue/create", response_model=QueueRead)
def enqueue_queued_message(
    payload: QueueCreate, db: DbSession, principal: PrincipalSession
) -> QueueRead:
    try:
        row = chat.queue.enqueue(
            db,
            principal.user_id,
            principal.tenant_id,
            payload.thread_id,
            payload.content.model_dump(),
        )
    except chat.queue.NotFound as exc:
        raise HTTPException(status_code=404, detail="thread not found") from exc
    except chat.queue.QueueFull as exc:
        raise HTTPException(status_code=422, detail="queue is full") from exc
    return _queue_out(row)


@router.get("/queue/get", response_model=list[QueueRead])
def get_queued_messages(
    thread_id: UUID, db: DbSession, principal: PrincipalSession
) -> list[QueueRead]:
    try:
        rows = chat.queue.list_for_thread(db, principal.user_id, thread_id)
    except chat.queue.NotFound as exc:
        raise HTTPException(status_code=404, detail="thread not found") from exc
    return [_queue_out(row) for row in rows]


@router.patch("/queue/update/{entry_id}", response_model=QueueRead)
def update_queued_message(
    entry_id: UUID, payload: QueueUpdate, db: DbSession, principal: PrincipalSession
) -> QueueRead:
    try:
        row = chat.queue.update(db, principal.user_id, entry_id, payload.content.model_dump())
    except chat.queue.NotFound as exc:
        raise HTTPException(status_code=404, detail="queued message not found") from exc
    return _queue_out(row)


@router.delete("/queue/delete/{entry_id}", status_code=204)
def delete_queued_message(entry_id: UUID, db: DbSession, principal: PrincipalSession) -> None:
    try:
        chat.queue.remove(db, principal.user_id, entry_id)
    except chat.queue.NotFound as exc:
        raise HTTPException(status_code=404, detail="queued message not found") from exc


@router.post("/shares/create/{thread_id}", response_model=ShareCreateRead)
def create_share(thread_id: UUID, db: DbSession, principal: PrincipalSession) -> ShareCreateRead:
    try:
        _share, token = chat.shares.create_or_refresh(
            db, principal.user_id, principal.tenant_id, thread_id
        )
    except chat.threads.NotFound as exc:
        raise HTTPException(status_code=404, detail="thread not found") from exc
    return ShareCreateRead(token=token, path=f"/share/{token}")


@router.get("/shares/get/{thread_id}", response_model=ShareStatusRead)
def get_share(thread_id: UUID, db: DbSession, principal: PrincipalSession) -> ShareStatusRead:
    try:
        shared = chat.shares.is_shared(db, principal.user_id, principal.tenant_id, thread_id)
    except chat.threads.NotFound as exc:
        raise HTTPException(status_code=404, detail="thread not found") from exc
    return ShareStatusRead(shared=shared)


@router.delete("/shares/delete/{thread_id}", status_code=204)
def delete_share(thread_id: UUID, db: DbSession, principal: PrincipalSession) -> None:
    try:
        chat.shares.revoke(db, principal.user_id, principal.tenant_id, thread_id)
    except chat.threads.NotFound as exc:
        raise HTTPException(status_code=404, detail="thread not found") from exc
    except chat.shares.NotFound as exc:
        raise HTTPException(status_code=404, detail="share not found") from exc
