"""Completion rules: caps, SSE parsing, and the reply stream lifecycle."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

import anyio
from sqlalchemy.orm import Session

from api.chat.gateway import GatewayError
from api.chat.threads import append_message, replace_history
from api.chat.tools import ArtifactSink, collect_calls, save_calls
from api.models import ChatThread

# Plain markdown: the chat renders markdown; component output is off.
SYSTEM_PROMPT = (
    "You are taipan, the assistant in this web app. Answer in plain "
    "markdown with short sentences and simple words. Use lists and tables "
    "when they help. Never invent features of the app. When the user "
    "asks for a document or table to keep, save it with the "
    "save_artifact tool."
)

MAX_MESSAGES = 200
MAX_TOTAL_CHARS = 200_000
# Attachments: AG-UI binary parts per user message, and the bytes the
# resolver may hand the model as base64 (images plus native PDFs).
MAX_BINARY_PARTS = 5
MAX_RESOLVED_BYTES = 20 * 1024 * 1024

_DATA_PREFIX = b"data: "

log = logging.getLogger(__name__)


class MessageCapError(ValueError):
    """The incoming history exceeds the pinned caps."""


def validate(incoming: list[dict]) -> None:
    if len(incoming) > MAX_MESSAGES:
        raise MessageCapError(f"more than {MAX_MESSAGES} messages")
    total = sum(len(json.dumps(message)) for message in incoming)
    if total > MAX_TOTAL_CHARS:
        raise MessageCapError(f"history larger than {MAX_TOTAL_CHARS} characters")
    for message in incoming:
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        count = sum(
            1 for part in content if isinstance(part, dict) and part.get("type") == "binary"
        )
        if count > MAX_BINARY_PARTS:
            raise MessageCapError(f"more than {MAX_BINARY_PARTS} attachments in one message")


def prepare(incoming: list[dict]) -> list[dict]:
    # tool_calls replay only into stored history: upstream rejects them without tool results.
    upstream = [_upstream_safe(message) for message in incoming if message.get("role") != "tool"]
    return [{"role": "system", "content": SYSTEM_PROMPT}, *upstream]


def _upstream_safe(message: dict) -> dict:
    cleaned = {key: value for key, value in message.items() if key != "tool_calls"}
    if cleaned.get("role") == "assistant" and cleaned.get("content") is None:
        cleaned["content"] = ""
    return cleaned


def assistant_text(raw: bytes) -> str:
    """Join the text deltas of an OpenAI SSE body; unknown lines are skipped."""
    parts: list[str] = []
    for line in raw.split(b"\n"):
        if not line.startswith(_DATA_PREFIX):
            continue
        payload = line[len(_DATA_PREFIX) :].strip()
        if payload == b"[DONE]":
            continue
        try:
            event = json.loads(payload)
        except ValueError:
            continue
        delta = (event.get("choices") or [{}])[0].get("delta", {})
        if isinstance(delta.get("content"), str):
            parts.append(delta["content"])
    return "".join(parts)


def error_event(message: str) -> bytes:
    payload = json.dumps({"error": {"message": message, "type": "gateway_error"}})
    return b"data: " + payload.encode() + b"\n\n"


async def stream_reply(
    db: Session,
    thread: ChatThread,
    incoming: list[dict],
    upstream: AsyncIterator[bytes],
    sink: ArtifactSink | None = None,
) -> AsyncIterator[bytes]:
    """Relay upstream bytes; store the reply only when bytes reached the client."""
    buffer = bytearray()
    started = False
    try:
        async for chunk in upstream:
            started = True
            buffer.extend(chunk)
            yield chunk
    except GatewayError as exc:
        # Before the first byte the route can 502; after it, only an in-stream event.
        if not started:
            raise
        # The client already saw these bytes; the partial reply and any
        # closed tool calls are honest history, so they persist too. A
        # persist failure must not swallow the gateway error frame.
        try:
            _persist(db, thread, incoming, buffer, sink)
        except Exception:
            log.exception("partial reply persist failed")
        yield error_event(str(exc))
        return
    except BaseException:
        _persist(db, thread, incoming, buffer, sink)
        raise
    else:
        _persist(db, thread, incoming, buffer, sink)
    finally:
        # Shielded: a client abort must still let the upstream cancel finish.
        with anyio.CancelScope(shield=True):
            await upstream.aclose()


def _persist(
    db: Session,
    thread: ChatThread,
    incoming: list[dict],
    buffer: bytearray,
    sink: ArtifactSink | None,
) -> None:
    # Own commit: a cancelled request rolls the request transaction back.
    replace_history(db, thread, incoming)
    raw = bytes(buffer)
    calls = collect_calls(raw)
    text = assistant_text(raw)
    if text or calls:
        # tool_calls ride along verbatim so the tool card replays on reload.
        message: dict = {"role": "assistant", "content": text}
        if calls:
            message["tool_calls"] = calls
        append_message(db, thread, message)
    db.commit()
    # After the reply commit: a failed upsert can never cost the history.
    if sink is not None and calls:
        save_calls(db, sink, thread_id=thread.id, calls=calls)
