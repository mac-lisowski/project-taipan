"""Completion rules: caps, SSE parsing, and the reply stream lifecycle."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import anyio
from sqlalchemy.orm import Session

from api.chat.gateway import GatewayError
from api.chat.threads import append_message, replace_history
from api.models import ChatThread

# The model answers with the chat component library, not long prose.
SYSTEM_PROMPT = (
    "You are a chat assistant in a web app. Compose answers from the chat "
    "component library: use steps for procedures, callouts for warnings and "
    "tips, and offer follow-up suggestions when they help. Keep prose short "
    "and prefer components over long paragraphs."
)

MAX_MESSAGES = 200
MAX_TOTAL_CHARS = 200_000

_DATA_PREFIX = b"data: "


class MessageCapError(ValueError):
    """The incoming history exceeds the pinned caps."""


def validate(incoming: list[dict]) -> None:
    if len(incoming) > MAX_MESSAGES:
        raise MessageCapError(f"more than {MAX_MESSAGES} messages")
    total = sum(len(json.dumps(message)) for message in incoming)
    if total > MAX_TOTAL_CHARS:
        raise MessageCapError(f"history larger than {MAX_TOTAL_CHARS} characters")


def prepare(incoming: list[dict]) -> list[dict]:
    return [{"role": "system", "content": SYSTEM_PROMPT}, *incoming]


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
) -> AsyncIterator[bytes]:
    """Relay upstream bytes; store the reply only when bytes reached the client."""
    buffer = bytearray()
    try:
        async for chunk in upstream:
            buffer.extend(chunk)
            yield chunk
    except GatewayError as exc:
        # Nothing is stored: the stored history keeps its pre-run shape.
        yield error_event(str(exc))
        return
    except BaseException:
        _persist(db, thread, incoming, buffer)
        raise
    else:
        _persist(db, thread, incoming, buffer)
    finally:
        # Shielded: a client abort must still let the upstream cancel finish.
        with anyio.CancelScope(shield=True):
            await upstream.aclose()


def _persist(db: Session, thread: ChatThread, incoming: list[dict], buffer: bytearray) -> None:
    # Own commit: a cancelled request rolls the request transaction back.
    replace_history(db, thread, incoming)
    text = assistant_text(bytes(buffer))
    if text:
        append_message(db, thread, {"role": "assistant", "content": text})
    db.commit()
