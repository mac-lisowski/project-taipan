"""Chat completion: validated history in, gateway SSE bytes out."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from api import chat
from api.authz import Principal, current_principal
from api.chat.gateway import GatewayDep
from api.db import DbSession
from api.schemas import CompletionIn

PrincipalSession = Annotated[Principal, Depends(current_principal)]

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/complete")
def complete(
    payload: CompletionIn, db: DbSession, principal: PrincipalSession, gateway: GatewayDep
) -> StreamingResponse:
    try:
        thread = chat.threads.get(db, principal.user_id, payload.thread_id)
    except chat.threads.NotFound as exc:
        raise HTTPException(status_code=404, detail="thread not found") from exc
    incoming = [message.model_dump() for message in payload.messages]
    try:
        chat.complete.validate(incoming)
    except chat.complete.MessageCapError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    upstream = gateway.stream(chat.complete.prepare(incoming))
    return StreamingResponse(
        chat.complete.stream_reply(db, thread, incoming, upstream),
        media_type="text/event-stream",
    )
