"""Attachment resolution: AG-UI binary parts become model-ready parts.

History stores parts verbatim; only the copy sent to the gateway is
rewritten here, so a model's capability flags never mutate the thread.
"""

from __future__ import annotations

import base64
import io
import json
import uuid
from typing import Any

from pypdf import PdfReader
from sqlalchemy.orm import Session
from storage import ObjectStore

from api import files
from api.authz import Principal
from api.chat.complete import MAX_RESOLVED_BYTES, MAX_TOTAL_CHARS, MessageCapError
from api.models import File

__all__ = ["fetch_bytes", "resolve_parts"]

_PDF_MIME = "application/pdf"
_TEXT_MIME = "text/plain"
_UNKNOWN_MIME = "application/octet-stream"


def resolve_parts(
    session: Session,
    store: ObjectStore,
    *,
    principal: Principal,
    messages: list[dict],
    flags: dict[str, bool],
) -> list[dict]:
    """Return messages with user binary parts mapped for the model's flags."""
    budget = _Budget(messages)
    resolved: list[dict] = []
    for message in messages:
        content = message.get("content")
        if message.get("role") != "user" or not isinstance(content, list):
            resolved.append(message)
            continue
        rewritten = [
            _resolve_part(
                session, store, principal=principal, part=part, flags=flags, budget=budget
            )
            for part in content
        ]
        resolved.append({**message, "content": rewritten})
    return resolved


def fetch_bytes(
    session: Session, store: ObjectStore, file_id: object, principal: Principal
) -> tuple[File, bytes] | None:
    """Read a registry file fully; any failure answers None for a marker."""
    try:
        row, content = files.open(session, store, uuid.UUID(str(file_id)), principal=principal)
        with content as (stream, _stat):
            return row, stream.read()
    except Exception:  # noqa: BLE001 - any fetch failure degrades to a marker, never a 500
        return None


def _resolve_part(
    session: Session,
    store: ObjectStore,
    *,
    principal: Principal,
    part: Any,
    flags: dict[str, bool],
    budget: _Budget,
) -> Any:
    if not isinstance(part, dict) or part.get("type") != "binary":
        return part
    filename = str(part.get("filename") or "attachment")
    mime = str(part.get("mimeType") or _UNKNOWN_MIME).lower()
    if part.get("id") is None:
        return _marker(filename, mime, None, budget)
    fetched = fetch_bytes(session, store, part["id"], principal)
    if fetched is None:
        return _marker(filename, mime, None, budget)
    row, data = fetched
    # The row's declared fields are truth; part mimeType/filename is client text.
    mime = (row.content_type or mime).lower()
    filename = row.filename or filename
    if mime.startswith("image/"):
        if flags.get("vision"):
            budget.take_binary(len(data))
            url = f"data:{mime};base64,{base64.b64encode(data).decode()}"
            return {"type": "image_url", "image_url": {"url": url}}
        return _marker(filename, mime, row.size_bytes, budget)
    if mime == _PDF_MIME:
        if flags.get("pdf_input"):
            budget.take_binary(len(data))
            return {
                "type": "file",
                "file": {
                    "filename": filename,
                    "file_data": f"data:{_PDF_MIME};base64,{base64.b64encode(data).decode()}",
                },
            }
        text = _pdf_text(data)
        if text is None:
            return _marker(filename, mime, row.size_bytes, budget)
        return _attachment_text(filename, text, budget)
    if mime == _TEXT_MIME:
        return _attachment_text(filename, data.decode("utf-8", errors="replace"), budget)
    return _marker(filename, mime, row.size_bytes, budget)


def _pdf_text(data: bytes) -> str | None:
    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:  # noqa: BLE001 - a failed extract degrades to the same marker
        return None


def _attachment_text(filename: str, text: str, budget: _Budget) -> dict:
    body = f"Attachment {filename}:\n```\n{text}\n```"
    budget.take_text(body)
    return {"type": "text", "text": body}


def _marker(filename: str, mime: str, size: int | None, budget: _Budget) -> dict:
    shown = f"{size} B" if size is not None else "unknown size"
    body = f"Attachment {filename} ({mime}, {shown}) not sent to the model."
    budget.take_text(body)
    return {"type": "text", "text": body}


class _Budget:
    """Per-request resolved caps: binary bytes and the text allowance."""

    def __init__(self, messages: list[dict]) -> None:
        self._binary = 0
        self._text_left = MAX_TOTAL_CHARS - sum(len(json.dumps(m)) for m in messages)

    def take_binary(self, size: int) -> None:
        self._binary += size
        if self._binary > MAX_RESOLVED_BYTES:
            raise MessageCapError(f"resolved attachments over {MAX_RESOLVED_BYTES} bytes")

    def take_text(self, text: str) -> None:
        self._text_left -= len(text)
        if self._text_left < 0:
            raise MessageCapError(f"resolved history over {MAX_TOTAL_CHARS} characters")
