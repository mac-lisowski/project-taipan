"""Session-scoped /api/files routes: upload, list, metadata, content, delete.

Thin: policy, choreography, and visibility live in ``api.files``; these
routes map service errors to status codes and pin the response headers.
"""

from collections.abc import Iterator
from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi import File as FileField
from fastapi.responses import StreamingResponse
from storage import ObjectContent, ObjectStore

from api import files
from api.authz import Principal, current_principal
from api.config import get_config
from api.db import DbSession
from api.files.store import get_object_store
from api.models import File
from api.schemas import FileOut, FilePageOut

PrincipalSession = Annotated[Principal, Depends(current_principal)]
StoreDep = Annotated[ObjectStore, Depends(get_object_store)]

router = APIRouter(prefix="/files", tags=["files"])


def _out(row: File) -> FileOut:
    return FileOut.model_validate(row)


@router.post("", response_model=FileOut, status_code=201)
def upload_file(
    db: DbSession,
    principal: PrincipalSession,
    store: StoreDep,
    purpose: Annotated[str, Form()],
    file: Annotated[UploadFile, FileField()],
    scope: Annotated[str, Form()] = "user",
) -> FileOut:
    try:
        row = files.store_upload(
            db,
            store,
            bucket=get_config().storage.s3_bucket,
            tenant_id=principal.tenant_id,
            user_id=principal.user_id,
            purpose=purpose,
            scope=scope,
            filename=file.filename or "file",
            content_type=file.content_type or "application/octet-stream",
            upload=file,
        )
    except files.TooLarge as exc:
        raise HTTPException(status_code=413, detail="file too large") from exc
    except files.UnsupportedType as exc:
        raise HTTPException(status_code=415, detail="unsupported content type") from exc
    except (files.PurposeNotAllowed, files.ScopeNotAllowed) as exc:
        raise HTTPException(status_code=400, detail="purpose or scope not allowed") from exc
    return _out(row)


@router.get("", response_model=FilePageOut)
def list_files(
    db: DbSession,
    principal: PrincipalSession,
    purpose: str | None = None,
    scope: str | None = None,
    cursor: str | None = None,
    limit: int | None = None,
) -> FilePageOut:
    try:
        page, next_cursor = files.list_page(
            db, principal=principal, purpose=purpose, scope=scope, cursor=cursor, limit=limit
        )
    except files.InvalidCursor as exc:
        raise HTTPException(status_code=400, detail="invalid cursor") from exc
    return FilePageOut(files=[_out(row) for row in page], next_cursor=next_cursor)


@router.get("/{file_id}", response_model=FileOut)
def get_file(file_id: UUID, db: DbSession, principal: PrincipalSession) -> FileOut:
    # Metadata reads the row only; a missing object still resolves.
    try:
        return _out(files.get(db, file_id, principal=principal))
    except files.NotFound as exc:
        raise HTTPException(status_code=404, detail="file not found") from exc


@router.get("/{file_id}/content")
def get_file_content(
    file_id: UUID, db: DbSession, principal: PrincipalSession, store: StoreDep
) -> StreamingResponse:
    row, content = _open(db, store, file_id, principal)
    headers = {
        "Content-Type": row.content_type,
        "Content-Length": str(row.size_bytes),
        "Content-Disposition": _disposition(row.content_type, row.filename),
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private",
    }
    return StreamingResponse(_stream(content), headers=headers)


@router.delete("/{file_id}", status_code=204)
def delete_file(file_id: UUID, db: DbSession, principal: PrincipalSession, store: StoreDep) -> None:
    try:
        files.delete(db, store, file_id, principal=principal)
    except files.NotFound as exc:
        raise HTTPException(status_code=404, detail="file not found") from exc


def _open(
    db: DbSession, store: ObjectStore, file_id: UUID, principal: Principal
) -> tuple[File, ObjectContent]:
    try:
        return files.open(db, store, file_id, principal=principal)
    except (files.NotFound, files.ObjectMissing) as exc:
        raise HTTPException(status_code=404, detail="file not found") from exc


def _disposition(content_type: str, filename: str) -> str:
    mime = content_type.split(";", 1)[0].strip().lower()
    kind = "inline" if mime.startswith("image/") else "attachment"
    return f"{kind}; filename*=UTF-8''{quote(filename)}"


def _stream(content: ObjectContent) -> Iterator[bytes]:
    # Close the object stream even when the client disconnects mid-stream.
    with content as (stream, _stat):
        while chunk := stream.read(files.CHUNK_BYTES):
            yield chunk
