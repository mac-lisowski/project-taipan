"""Chat completion: validated history in, gateway SSE bytes out."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from storage import ObjectStore

from api import chat
from api.authz import Principal, current_principal
from api.chat.gateway import GatewayDep, GatewayError
from api.chat.models import ModelCatalogDep
from api.config import get_config
from api.db import DbSession
from api.files.store import get_object_store
from api.schemas import CompletionIn

PrincipalSession = Annotated[Principal, Depends(current_principal)]
StoreDep = Annotated[ObjectStore, Depends(get_object_store)]

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/models")
async def models(principal: PrincipalSession, catalog: ModelCatalogDep) -> list[dict]:
    return await catalog.list()


@router.post("/complete")
async def complete(
    payload: CompletionIn,
    db: DbSession,
    principal: PrincipalSession,
    gateway: GatewayDep,
    catalog: ModelCatalogDep,
    store: StoreDep,
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
    if payload.model is not None:
        # The 422 names the same set GET /models serves; the gateway still enforces.
        allowed = await catalog.allowed_ids()
        if payload.model not in allowed:
            raise HTTPException(
                status_code=422,
                detail=f"unknown model {payload.model!r}; allowed: {', '.join(sorted(allowed))}",
            )
    flags = await catalog.capabilities(payload.model or get_config().chat.chat_model)
    try:
        # History keeps the binary parts verbatim; only the gateway copy resolves.
        resolved = chat.attachments.resolve_parts(
            db, store, principal=principal, messages=incoming, flags=flags
        )
    except chat.complete.MessageCapError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    # Tools advertise only when the model can call them; tool_choice needs its
    # own flag. The sink rides along so closed calls can upsert artifacts.
    tools = [chat.tools.SAVE_ARTIFACT_TOOL] if flags.get("function_calling") else None
    sink = (
        chat.tools.ArtifactSink(
            store=store, principal=principal, bucket=get_config().storage.s3_bucket
        )
        if tools is not None
        else None
    )
    upstream = chat.complete.stream_reply(
        db,
        thread,
        incoming,
        gateway.stream(
            chat.complete.prepare(resolved),
            payload.model,
            tools=tools,
            tool_choice="auto" if flags.get("tool_choice") else None,
        ),
        sink=sink,
    )
    try:
        # First pull opens the gateway connection, so a dead gateway fails here.
        first = await anext(upstream)
    except StopAsyncIteration:
        first = b""
    except GatewayError as exc:
        raise HTTPException(status_code=502, detail="gateway is unavailable") from exc

    async def relay():
        if first:
            yield first
        try:
            async for chunk in upstream:
                yield chunk
        finally:
            # Deterministic close: client abort must reach the persist path.
            await upstream.aclose()

    return StreamingResponse(relay(), media_type="text/event-stream")
