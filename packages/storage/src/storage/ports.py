"""Object store seam: one port, typed results, typed errors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Protocol


class StorageError(Exception):
    """Base error for every object-store failure."""


class ObjectNotFound(StorageError):
    """The requested object does not exist."""


@dataclass(frozen=True)
class StoredObject:
    """A stored object's identity and pinned metadata."""

    bucket: str
    key: str
    content_type: str
    size: int


@dataclass(frozen=True)
class ObjectStat:
    """Metadata returned next to a fetched byte stream."""

    content_type: str
    size: int


class ObjectContent:
    """Context manager yielding ``(stream, stat)``; closes the stream on exit."""

    def __init__(self, stream: BinaryIO, stat: ObjectStat) -> None:
        self._stream = stream
        self._stat = stat

    def __enter__(self) -> tuple[BinaryIO, ObjectStat]:
        return self._stream, self._stat

    def __exit__(self, *_: object) -> None:
        self._stream.close()


class ObjectStore(Protocol):
    """Single seam for all object bytes. Adapters implement this."""

    def put(
        self,
        bucket: str,
        key: str,
        data: BinaryIO,
        *,
        content_type: str,
        size: int,
    ) -> StoredObject: ...

    def get(self, bucket: str, key: str) -> ObjectContent: ...

    def delete(self, bucket: str, key: str) -> None: ...
