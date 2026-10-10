"""Artifact download payloads: markdown for documents, CSV for tables.

The stored object is always JSON; the download route re-encodes it into
the format a user can open directly.
"""

from __future__ import annotations

import csv
import io
import json
import re
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy.orm import Session
from storage import ObjectStore

from api.artifacts import service

if TYPE_CHECKING:
    from api.authz import Principal

MARKDOWN_MEDIA = "text/markdown; charset=utf-8"
CSV_MEDIA = "text/csv; charset=utf-8"


def build(
    session: Session, store: ObjectStore, artifact_id: UUID, *, principal: Principal
) -> tuple[str, str, bytes]:
    """Return (filename, media_type, bytes) for an artifact the caller owns."""
    row, content = service.get(session, store, artifact_id, principal=principal)
    slug = _slug(row.title)
    if row.type == service.TABLE_TYPE:
        return f"{slug}.csv", CSV_MEDIA, _csv(content)
    return f"{slug}.md", MARKDOWN_MEDIA, _markdown(content)


def _markdown(content: Any) -> bytes:
    markdown = content.get("markdown") if isinstance(content, dict) else None
    return (markdown if isinstance(markdown, str) else "").encode()


def _csv(content: Any) -> bytes:
    rows = content.get("rows") if isinstance(content, dict) else None
    keys: list[Any] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        for key in row:
            if key not in keys:
                keys.append(key)
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow([str(key) for key in keys])
    for row in rows or []:
        if isinstance(row, dict):
            writer.writerow([_cell(row.get(key)) for key in keys])
    return out.getvalue().encode()


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict | list):
        return json.dumps(value)
    return str(value)


def _slug(title: str) -> str:
    # ASCII-only slug keeps the Content-Disposition filename header simple.
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "artifact"
