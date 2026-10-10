"""Single-file reads and keyset listing, scope-filtered by principal.

The list cursor is a base64 blob over ``(created_at, id)``, the same
shape as chat threads. ``open`` additionally fetches the object bytes;
``get`` is metadata-only so a missing object still lists and reads.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select, tuple_
from sqlalchemy.orm import Session
from storage import ObjectContent, ObjectNotFound, ObjectStore

from api.authz import Principal
from api.files.errors import NotFound, ObjectMissing
from api.files.policies import SCOPE_TENANT, SCOPE_USER
from api.models import File

__all__ = [
    "DEFAULT_PAGE",
    "MAX_PAGE",
    "InvalidCursor",
    "get",
    "list_page",
    "open",
]

DEFAULT_PAGE = 50
MAX_PAGE = 200


class InvalidCursor(Exception):
    """The opaque list cursor is unreadable."""


def get(session: Session, file_id: UUID, *, principal: Principal) -> File:
    """Return the metadata row when the principal may read it."""
    row = session.get(File, file_id)
    if row is None or not _visible(row, principal):
        raise NotFound(file_id)
    return row


def open(
    session: Session, store: ObjectStore, file_id: UUID, *, principal: Principal
) -> tuple[File, ObjectContent]:
    """Return the row and an open byte stream when the principal may read it."""
    row = get(session, file_id, principal=principal)
    try:
        content = store.get(row.bucket, row.object_key)
    except ObjectNotFound as exc:
        raise ObjectMissing(str(exc)) from exc
    return row, content


def list_page(
    session: Session,
    *,
    principal: Principal,
    purpose: str | None = None,
    scope: str | None = None,
    cursor: str | None = None,
    limit: int | None = None,
) -> tuple[list[File], str | None]:
    """Files the principal may read, newest first, keyset paged."""
    query = (
        select(File).where(_readable(principal)).order_by(File.created_at.desc(), File.id.desc())
    )
    if purpose is not None:
        query = query.where(File.purpose == purpose)
    if scope is not None:
        query = query.where(File.scope == scope)
    if cursor is not None:
        query = query.where(tuple_(File.created_at, File.id) < _decode_cursor(cursor))
    page_size = _clamp(limit)
    rows = list(session.scalars(query.limit(page_size + 1)).all())
    has_more = len(rows) > page_size
    page = rows[:page_size]
    return page, _encode_cursor(page[-1]) if has_more else None


def _visible(row: File, principal: Principal) -> bool:
    """The read rule shared by ``get`` and ``open``; delete is stricter."""
    if row.scope == SCOPE_USER:
        return row.created_by_user_id == principal.user_id
    if row.scope == SCOPE_TENANT:
        return row.tenant_id == principal.tenant_id
    return False


def _readable(principal: Principal):
    return or_(
        and_(File.scope == SCOPE_USER, File.created_by_user_id == principal.user_id),
        and_(File.scope == SCOPE_TENANT, File.tenant_id == principal.tenant_id),
    )


def _clamp(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_PAGE
    return max(1, min(limit, MAX_PAGE))


def _encode_cursor(row: File) -> str:
    payload = json.dumps({"t": row.created_at.isoformat(), "id": str(row.id)})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        stamp = datetime.fromisoformat(payload["t"])
        # Naive stamps compare against timestamptz via session timezone; refuse them.
        if stamp.tzinfo is None:
            raise ValueError("cursor timestamp lacks a timezone")
        return stamp, UUID(payload["id"])
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise InvalidCursor(cursor) from exc
