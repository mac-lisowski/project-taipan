"""Unauthenticated reads: the share token itself is the credential."""

from fastapi import APIRouter, HTTPException

from api import chat
from api.db import DbSession
from api.schemas import SharedThreadRead

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/threads/{token}", response_model=SharedThreadRead)
def read_shared_thread(token: str, db: DbSession) -> SharedThreadRead:
    try:
        share = chat.shares.read_snapshot(db, token)
    except chat.shares.NotFound as exc:
        raise HTTPException(status_code=404, detail="share not found") from exc
    return SharedThreadRead(title=share.title, messages=share.snapshot)
