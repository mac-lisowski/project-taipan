"""Artifact models for the /api/artifacts surface.

The wire shape is the SDK contract: camelCase keys, ``threadId`` a plain
string (``""`` when the artifact outlived its thread), ``updatedAt`` an
epoch float like the threads reads.
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ArtifactSummaryOut(BaseModel):
    id: UUID
    title: str
    type: str
    thread_id: str = Field(serialization_alias="threadId")
    updated_at: float = Field(serialization_alias="updatedAt")


class ArtifactOut(ArtifactSummaryOut):
    # The stored {"markdown": ...} / {"rows": [...]} body, parsed JSON.
    content: dict[str, Any]


class ArtifactListOut(BaseModel):
    artifacts: list[ArtifactSummaryOut]
    next_cursor: str | None = Field(default=None, serialization_alias="nextCursor")


class ArtifactPatch(BaseModel):
    # Update is content-only; title and type are create-time facts.
    content: dict[str, Any]
