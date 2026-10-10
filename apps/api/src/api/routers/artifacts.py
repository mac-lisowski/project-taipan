"""Session-scoped /api/artifacts routes: list, read, patch, delete.

Thin: row+file+object choreography lives in ``api.artifacts``; these
routes map service errors to status codes and emit the SDK shape.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from storage import ObjectStore

from api import artifacts
from api.authz import Principal, current_principal
from api.config import get_config
from api.db import DbSession
from api.files.store import get_object_store
from api.models import ChatArtifact
from api.schemas import ArtifactListOut, ArtifactOut, ArtifactPatch, ArtifactSummaryOut

PrincipalSession = Annotated[Principal, Depends(current_principal)]
StoreDep = Annotated[ObjectStore, Depends(get_object_store)]

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


def _fields(row: ChatArtifact) -> dict[str, Any]:
    return {
        "id": row.id,
        "title": row.title,
        "type": row.type,
        # A dead thread reads as "" so the SDK hides the go-to-thread affordance.
        "thread_id": str(row.thread_id) if row.thread_id is not None else "",
        "updated_at": row.updated_at.timestamp(),
    }


def _summary(row: ChatArtifact) -> ArtifactSummaryOut:
    return ArtifactSummaryOut(**_fields(row))


@router.get("", response_model=ArtifactListOut)
def list_artifacts(
    db: DbSession,
    principal: PrincipalSession,
    name: str | None = None,
    type: Annotated[list[str] | None, Query()] = None,
    cursor: str | None = None,
    limit: int | None = None,
) -> ArtifactListOut:
    try:
        page, next_cursor = artifacts.list_page(
            db, principal=principal, name=name, types=type, cursor=cursor, limit=limit
        )
    except artifacts.InvalidCursor as exc:
        raise HTTPException(status_code=400, detail="invalid cursor") from exc
    return ArtifactListOut(artifacts=[_summary(row) for row in page], next_cursor=next_cursor)


@router.get("/{artifact_id}", response_model=ArtifactOut)
def get_artifact(
    artifact_id: UUID, db: DbSession, principal: PrincipalSession, store: StoreDep
) -> ArtifactOut:
    try:
        row, content = artifacts.get(db, store, artifact_id, principal=principal)
    except (artifacts.NotFound, artifacts.ObjectMissing) as exc:
        raise HTTPException(status_code=404, detail="artifact not found") from exc
    return ArtifactOut(**_fields(row), content=content)


@router.patch("/{artifact_id}", response_model=ArtifactSummaryOut)
def update_artifact(
    artifact_id: UUID,
    payload: ArtifactPatch,
    db: DbSession,
    principal: PrincipalSession,
    store: StoreDep,
) -> ArtifactSummaryOut:
    try:
        row = artifacts.update(
            db,
            store,
            artifact_id,
            principal=principal,
            bucket=get_config().storage.s3_bucket,
            content=payload.content,
        )
    except artifacts.NotFound as exc:
        raise HTTPException(status_code=404, detail="artifact not found") from exc
    return _summary(row)


@router.delete("/{artifact_id}", status_code=204)
def delete_artifact(
    artifact_id: UUID, db: DbSession, principal: PrincipalSession, store: StoreDep
) -> None:
    try:
        artifacts.delete(db, store, artifact_id, principal=principal)
    except artifacts.NotFound as exc:
        raise HTTPException(status_code=404, detail="artifact not found") from exc
