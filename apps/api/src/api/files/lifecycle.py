"""File lifecycle: detach a user's content, purge a dying tenant's files.

``detach_user`` drops the uploader's private rows and objects, then nulls
their shared attribution. ``detach_tenant`` purges every file in a dying
tenant. Both run their mutations inside the victim tenant's scope, so the
flush guard passes under the caller's ambient scope. Objects delete under
``row.bucket``, never a caller guess: the row is the source of truth.
Objects go after the row flush but before the caller's commit; a failed
commit leaves rows pointing at dead objects, which consumers already
tolerate (a dangling object answers 404).
"""

from __future__ import annotations

import contextlib

from crypto import tenant_scope
from sqlalchemy import select
from sqlalchemy.orm import Session
from storage import ObjectStore

from api.files.policies import SCOPE_TENANT, SCOPE_USER
from api.models import File

__all__ = ["detach_tenant", "detach_user", "discard"]


def discard(store: ObjectStore, bucket: str, key: str) -> None:
    """Best-effort object delete; a storage outage never strands the API."""
    # The S3 adapter maps only S3Error; urllib3 transport errors arrive raw.
    with contextlib.suppress(Exception):
        store.delete(bucket, key)


def detach_user(session: Session, store: ObjectStore, *, user_id: int) -> None:
    """Purge the uploader's private rows+objects, then null their shared rows."""
    private = session.scalars(
        select(File).where(File.scope == SCOPE_USER, File.created_by_user_id == user_id)
    ).all()
    shared = session.scalars(
        select(File).where(File.scope == SCOPE_TENANT, File.created_by_user_id == user_id)
    ).all()
    _clear_uploader(session, shared)
    _delete_scoped(session, private)
    for row in private:
        discard(store, row.bucket, row.object_key)


def detach_tenant(session: Session, store: ObjectStore, *, tenant_id: str) -> None:
    """Purge every file row and object in a dying tenant."""
    rows = session.scalars(select(File).where(File.tenant_id == tenant_id)).all()
    with tenant_scope(tenant_id):
        for row in rows:
            session.delete(row)
        session.flush()
    for row in rows:
        discard(store, row.bucket, row.object_key)


def _clear_uploader(session: Session, rows: list[File]) -> None:
    """Null the uploader one tenant at a time: a flush spans a single scope."""
    for tenant_id, group in _by_tenant(rows).items():
        with tenant_scope(tenant_id):
            for row in group:
                row.created_by_user_id = None
            session.flush()


def _delete_scoped(session: Session, rows: list[File]) -> None:
    """Delete one tenant's rows at a time inside its own scope."""
    for tenant_id, group in _by_tenant(rows).items():
        with tenant_scope(tenant_id):
            for row in group:
                session.delete(row)
            session.flush()


def _by_tenant(rows: list[File]) -> dict[str, list[File]]:
    groups: dict[str, list[File]] = {}
    for row in rows:
        groups.setdefault(row.tenant_id, []).append(row)
    return groups
