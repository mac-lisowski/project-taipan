from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from api.models.chat import TITLE_MAX


class ChatMessageIn(BaseModel):
    # extra="allow" keeps the full OpenAI message shape for verbatim storage.
    model_config = ConfigDict(extra="allow")

    role: Literal["user", "assistant", "system"]
    content: str


class CompletionMessageIn(BaseModel):
    # extra="allow" keeps extras on the wire; parts arrays stay verbatim.
    model_config = ConfigDict(extra="allow")

    role: Literal["user", "assistant", "system"]
    content: str | list[Any]


class CompletionIn(BaseModel):
    thread_id: UUID = Field(alias="threadId")
    # The chat SDK always sends runId; it carries no storage role.
    run_id: str = Field(min_length=1, alias="runId")
    messages: list[CompletionMessageIn] = []


class ThreadCreate(BaseModel):
    messages: list[ChatMessageIn] = []


class ThreadRead(BaseModel):
    id: str
    title: str
    created_at: float = Field(serialization_alias="createdAt")


class ThreadListRead(BaseModel):
    threads: list[ThreadRead]
    next_cursor: str | None = Field(default=None, serialization_alias="nextCursor")


class ThreadUpdate(BaseModel):
    # The body is the full Thread; only the rename changes stored state.
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = None
    title: str = Field(min_length=1, max_length=TITLE_MAX)
    created_at: float | None = Field(default=None, alias="createdAt")


class QueueContent(BaseModel):
    # extra="allow" keeps the content dict verbatim; parts keys fit later.
    model_config = ConfigDict(extra="allow")

    text: str = Field(min_length=1)


class QueueCreate(BaseModel):
    thread_id: UUID = Field(alias="threadId")
    content: QueueContent


class QueueRead(BaseModel):
    id: str
    thread_id: str = Field(serialization_alias="threadId")
    seq: int
    content: QueueContent
    created_at: float = Field(serialization_alias="createdAt")


class QueueUpdate(BaseModel):
    content: QueueContent
