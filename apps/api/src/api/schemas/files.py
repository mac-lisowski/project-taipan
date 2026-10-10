"""File metadata read models for the /api/files surface."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    purpose: str
    scope: str
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    created_at: datetime


class FilePageOut(BaseModel):
    files: list[FileOut]
    next_cursor: str | None = None
