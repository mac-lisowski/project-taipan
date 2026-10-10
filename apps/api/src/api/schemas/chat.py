from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from api.models.chat import TITLE_MAX


class ChatMessageIn(BaseModel):
    # extra="allow" keeps the full OpenAI message shape for verbatim storage.
    model_config = ConfigDict(extra="allow")

    role: Literal["user", "assistant", "system"]
    content: str | list[Any]


class CompletionMessageIn(BaseModel):
    # extra="allow" keeps extras on the wire; parts arrays stay verbatim.
    model_config = ConfigDict(extra="allow")

    role: Literal["user", "assistant", "system"]
    # Replayed tool-only replies carry content null; prepare normalizes.
    content: str | list[Any] | None = None

    @model_validator(mode="after")
    def _null_only_for_assistant(self) -> "CompletionMessageIn":
        # A null user/system message would reach the gateway and 400 there.
        if self.role != "assistant" and self.content is None:
            raise ValueError("content is required")
        return self


class CompletionIn(BaseModel):
    thread_id: UUID = Field(alias="threadId")
    # The chat SDK always sends runId; it carries no storage role.
    run_id: str = Field(min_length=1, alias="runId")
    messages: list[CompletionMessageIn] = []
    # Optional model pick; the route checks it against the catalog's set.
    model: str | None = None


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
    # extra="allow" keeps the content dict verbatim; parts keys ride through.
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


class ShareCreateRead(BaseModel):
    token: str
    # The web app prefixes its own origin; the api returns the path only.
    path: str


class ShareStatusRead(BaseModel):
    shared: bool


class SharedThreadRead(BaseModel):
    # The response model is the leak guard: only these keys leave the api.
    title: str
    messages: list[dict]
