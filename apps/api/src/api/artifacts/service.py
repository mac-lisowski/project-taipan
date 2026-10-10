"""Chat artifacts service: owner-scoped CRUD over row, file, and object.

Each artifact row points at a ``files`` registry row (purpose
``artifact``, scope ``user``); the bytes are JSON at
``application/json`` under ``artifacts/{tenant_id}/``. Writes put the
object first so a failed commit never leaves a row without bytes.
``purge_user`` runs before ``files.detach_user`` inside
``users.remove``: RESTRICT on ``file_id`` would otherwise block the
private-file purge.
"""

from __future__ import annotations

import base64
import contextlib
import json
from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from crypto import tenant_scope
from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session
from storage import ObjectNotFound, ObjectStore

if TYPE_CHECKING:
    # Annotation-only: keeps users.service free of the FastAPI-coupled authz.
    from api.authz import Principal
from api.files.errors import ObjectMissing
from api.files.lifecycle import discard
from api.files.service import store_bytes
from api.models import ChatArtifact, File

__all__ = [
    "InvalidCursor",
    "NotFound",
    "ObjectMissing",
    "create",
    "delete",
    "get",
    "list_page",
    "purge_user",
    "update",
]

PURPOSE = "artifact"
CONTENT_TYPE = "application/json"
DEFAULT_PAGE = 50
MAX_PAGE = 200


class NotFound(Exception):
    """No artifact with this id for the calling user."""


class InvalidCursor(Exception):
    """The opaque list cursor is unreadable."""


def create(
    session: Session,
    store: ObjectStore,
    *,
    bucket: str,
    principal: Principal,
    type: str,
    title: str,
    content: Any,
    thread_id: UUID | None = None,
    commit: bool = True,
) -> ChatArtifact:
    """Store the body, then land the file and artifact rows in one transaction."""
    file_row = store_bytes(
        session,
        store,
        bucket=bucket,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        purpose=PURPOSE,
        filename=_filename(title),
        content_type=CONTENT_TYPE,
        data=json.dumps(content).encode(),
        commit=False,
    )
    row = ChatArtifact(
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        thread_id=thread_id,
        type=type,
        title=title,
        file_id=file_row.id,
    )
    try:
        with tenant_scope(principal.tenant_id):
            session.add(row)
            session.flush()
        if commit:
            session.commit()
    except BaseException:
        with contextlib.suppress(Exception):
            session.rollback()
        # The file row and object both belong to this transaction's casualty.
        discard(store, file_row.bucket, file_row.object_key)
        raise
    return row


def get(
    session: Session, store: ObjectStore, artifact_id: UUID, *, principal: Principal
) -> tuple[ChatArtifact, Any]:
    """Return the row plus its parsed JSON body when the principal owns it."""
    row = _owned(session, artifact_id, principal)
    file_row = session.get(File, row.file_id)
    if file_row is None:
        raise ObjectMissing(f"artifact {artifact_id} has no file row")
    try:
        content = store.get(file_row.bucket, file_row.object_key)
    except ObjectNotFound as exc:
        raise ObjectMissing(str(exc)) from exc
    with content as (stream, _stat):
        return row, json.loads(stream.read())


def list_page(
    session: Session,
    *,
    principal: Principal,
    name: str | None = None,
    types: Sequence[str] | None = None,
    cursor: str | None = None,
    limit: int | None = None,
) -> tuple[list[ChatArtifact], str | None]:
    """The caller's artifacts, most recently updated first, keyset paged."""
    query = (
        select(ChatArtifact)
        .where(ChatArtifact.user_id == principal.user_id)
        .order_by(ChatArtifact.updated_at.desc(), ChatArtifact.id.desc())
    )
    if name and name.strip():
        query = query.where(ChatArtifact.title.ilike(f"%{_escape_like(name.strip())}%"))
    if types:
        query = query.where(ChatArtifact.type.in_(types))
    if cursor is not None:
        query = query.where(
            tuple_(ChatArtifact.updated_at, ChatArtifact.id) < _decode_cursor(cursor)
        )
    page_size = _clamp(limit)
    rows = list(session.scalars(query.limit(page_size + 1)).all())
    has_more = len(rows) > page_size
    page = rows[:page_size]
    return page, _encode_cursor(page[-1]) if has_more else None


def update(
    session: Session,
    store: ObjectStore,
    artifact_id: UUID,
    *,
    principal: Principal,
    bucket: str,
    content: Any,
) -> ChatArtifact:
    """Write the new object, swap file_id, bump version, drop the old object."""
    row = _owned(session, artifact_id, principal)
    old = session.get(File, row.file_id)
    new = store_bytes(
        session,
        store,
        bucket=bucket,
        tenant_id=row.tenant_id,
        user_id=principal.user_id,
        purpose=PURPOSE,
        filename=_filename(row.title),
        content_type=CONTENT_TYPE,
        data=json.dumps(content).encode(),
        commit=False,
    )
    try:
        with tenant_scope(row.tenant_id):
            row.file_id = new.id
            row.version += 1
            if old is not None:
                session.delete(old)
            session.flush()
        session.commit()
    except BaseException:
        with contextlib.suppress(Exception):
            session.rollback()
        discard(store, new.bucket, new.object_key)
        raise
    if old is not None:
        discard(store, old.bucket, old.object_key)
    return row


def delete(
    session: Session, store: ObjectStore, artifact_id: UUID, *, principal: Principal
) -> None:
    """Artifact row first (RESTRICT), then the file row, then the object."""
    row = _owned(session, artifact_id, principal)
    file_row = session.get(File, row.file_id)
    location = (file_row.bucket, file_row.object_key) if file_row is not None else None
    try:
        with tenant_scope(row.tenant_id):
            session.delete(row)
            if file_row is not None:
                session.delete(file_row)
            session.flush()
        session.commit()
    except BaseException:
        with contextlib.suppress(Exception):
            session.rollback()
        raise
    if location is not None:
        discard(store, *location)


def purge_user(session: Session, store: ObjectStore, *, user_id: int) -> None:
    """Delete the user's artifact rows, then their file rows, then objects.

    Runs inside ``users.remove``'s transaction ahead of
    ``files.detach_user``, so RESTRICT on ``file_id`` never sees a live
    artifact when the private-file purge runs. No commit here: the
    caller owns the boundary.
    """
    rows = session.scalars(select(ChatArtifact).where(ChatArtifact.user_id == user_id)).all()
    files = (
        session.scalars(select(File).where(File.id.in_([r.file_id for r in rows]))).all()
        if rows
        else []
    )
    _delete_by_tenant(session, rows)
    _delete_by_tenant(session, files)
    for file_row in files:
        discard(store, file_row.bucket, file_row.object_key)


def _owned(session: Session, artifact_id: UUID, principal: Principal) -> ChatArtifact:
    # The user filter hides other people's artifacts behind a plain 404.
    row = session.scalar(
        select(ChatArtifact).where(
            ChatArtifact.id == artifact_id,
            ChatArtifact.user_id == principal.user_id,
        )
    )
    if row is None:
        raise NotFound(artifact_id)
    return row


def _filename(title: str) -> str:
    # Files requires a filename; the title is the navigable name.
    return f"{title}.json"


def _delete_by_tenant(session: Session, rows: Iterable) -> None:
    """One tenant's deletes per flush, inside that tenant's scope."""
    groups: dict[str, list] = {}
    for row in rows:
        groups.setdefault(row.tenant_id, []).append(row)
    for tenant_id, group in groups.items():
        with tenant_scope(tenant_id):
            for row in group:
                session.delete(row)
            session.flush()


def _escape_like(needle: str) -> str:
    """Escape LIKE wildcards so user input matches literally."""
    return needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _clamp(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_PAGE
    return max(1, min(limit, MAX_PAGE))


def _encode_cursor(row: ChatArtifact) -> str:
    payload = json.dumps({"t": row.updated_at.isoformat(), "id": str(row.id)})
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
