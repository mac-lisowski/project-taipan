"""save_artifact tool: advertised schema, fragment folding, artifact upserts.

The completion route advertises ``SAVE_ARTIFACT_TOOL`` when the resolved
model supports function calling. The model answers with streamed
``delta.tool_calls`` fragments; :func:`collect_calls` folds them per
``index`` and :func:`save_calls` writes one artifact row per closed call
through the artifacts service. Bytes relay to the client unchanged; the
API never fabricates a tool result message.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session
from storage import ObjectStore

from api import artifacts
from api.authz import Principal

__all__ = [
    "SAVE_ARTIFACT_TOOL",
    "ArtifactSink",
    "collect_calls",
    "save_calls",
]

log = logging.getLogger(__name__)

SAVE_ARTIFACT_NAME = "save_artifact"
DOCUMENT_TYPE = "taipan_document"
TABLE_TYPE = "taipan_table"

SAVE_ARTIFACT_TOOL = {
    "type": "function",
    "function": {
        "name": SAVE_ARTIFACT_NAME,
        "description": "Save a document or table the user asked for as a workspace artifact.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "type": {"type": "string", "enum": [DOCUMENT_TYPE, TABLE_TYPE]},
                "content": {
                    "description": (
                        "Markdown string for taipan_document; array of row "
                        "objects for taipan_table."
                    ),
                    # The schema can't tie the shape to `type`, but anyOf still
                    # steers generation away from scalars and nested junk.
                    "anyOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "object"}},
                    ],
                },
            },
            "required": ["title", "type", "content"],
            "additionalProperties": False,
        },
    },
}


@dataclass(frozen=True)
class ArtifactSink:
    """Persist target for streamed tool calls: store, identity, bucket."""

    store: ObjectStore
    principal: Principal
    bucket: str


def collect_calls(raw: bytes) -> list[dict]:
    """Fold ``delta.tool_calls`` fragments into one closed call per index."""
    calls: dict[int, dict[str, Any]] = {}
    order: list[int] = []
    for line in raw.split(b"\n"):
        if not line.startswith(b"data: "):
            continue
        payload = line[len(b"data: ") :].strip()
        if payload == b"[DONE]":
            continue
        try:
            event = json.loads(payload)
        except ValueError:
            continue
        delta = (event.get("choices") or [{}])[0].get("delta") or {}
        for fragment in delta.get("tool_calls") or []:
            if not isinstance(fragment, dict):
                continue
            index = fragment.get("index")
            if not isinstance(index, int):
                # Index-less fragments continue the open call; inventing a
                # fresh index would split one call into partial arguments.
                index = order[-1] if order else 0
            call = calls.get(index)
            if call is None:
                call = {
                    "id": None,
                    "type": "function",
                    "function": {"name": "", "arguments": ""},
                }
                calls[index] = call
                order.append(index)
            if fragment.get("id"):
                call["id"] = fragment["id"]
            if fragment.get("type"):
                call["type"] = fragment["type"]
            function = fragment.get("function") or {}
            # Some providers resend the whole name per fragment; first wins.
            if function.get("name") and not call["function"]["name"]:
                call["function"]["name"] = function["name"]
            if function.get("arguments"):
                call["function"]["arguments"] += function["arguments"]
    return [calls[index] for index in order]


def save_calls(session: Session, sink: ArtifactSink, *, thread_id: UUID, calls: list[dict]) -> None:
    """One new artifact row per closed save_artifact call; errors log, not raise."""
    for call in calls:
        function = call.get("function") or {}
        if function.get("name") != SAVE_ARTIFACT_NAME:
            continue
        try:
            args = json.loads(function.get("arguments") or "")
        except ValueError:
            log.warning("save_artifact call %r carried malformed arguments", call.get("id"))
            continue
        body = _body(args)
        if body is None:
            log.warning("save_artifact call %r args fail the content contract", call.get("id"))
            continue
        try:
            artifacts.create(
                session,
                sink.store,
                bucket=sink.bucket,
                principal=sink.principal,
                type=args["type"],
                title=str(args.get("title") or "Untitled"),
                content=body,
                thread_id=thread_id,
            )
        # A failed upsert must not kill the reply persist; it logs and moves on.
        except Exception:
            log.exception("artifact upsert for call %r failed", call.get("id"))


def _body(args: Any) -> dict | None:
    """Map tool args to the stored object shape; anything else is refused."""
    if not isinstance(args, dict):
        return None
    kind = args.get("type")
    content = args.get("content")
    if kind == DOCUMENT_TYPE and isinstance(content, str):
        return {"markdown": content}
    if kind == TABLE_TYPE and isinstance(content, list):
        return {"rows": content}
    return None
