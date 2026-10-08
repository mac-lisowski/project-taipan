"""Thin chat thread routes: the five storage endpoints, session scoped."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from api import chat
from api.authz import Principal, current_principal
from api.db import DbSession
from api.models import ChatThread
from api.schemas import ThreadCreate, ThreadListRead, ThreadRead, ThreadUpdate

PrincipalSession = Annotated[Principal, Depends(current_principal)]

router = APIRouter(prefix="/threads", tags=["chat"])


def _thread_out(thread: ChatThread) -> ThreadRead:
    return ThreadRead(
        id=str(thread.id), title=thread.title, created_at=thread.created_at.timestamp()
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
