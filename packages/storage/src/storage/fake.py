"""Fake adapter: objects in memory, no network."""

from __future__ import annotations

import io
from typing import BinaryIO

from storage.ports import (
    ObjectContent,
    ObjectNotFound,
    ObjectStat,
    ObjectStore,
    StoredObject,
)


class FakeObjectStore(ObjectStore):
    """Captures object bytes in memory for local dev and tests."""

    def __init__(self) -> None:
        self._objects: dict[tuple[str, str], tuple[bytes, str]] = {}

    def put(
        self,
        bucket: str,
        key: str,
        data: BinaryIO,
        *,
        content_type: str,
        size: int,
    ) -> StoredObject:
        payload = data.read(size)
        self._objects[(bucket, key)] = (payload, content_type)
        return StoredObject(bucket=bucket, key=key, content_type=content_type, size=len(payload))

    def get(self, bucket: str, key: str) -> ObjectContent:
        try:
            payload, content_type = self._objects[(bucket, key)]
        except KeyError:
            raise ObjectNotFound(f"no object at {bucket}/{key}") from None
        stat = ObjectStat(content_type=content_type, size=len(payload))
        return ObjectContent(io.BytesIO(payload), stat)

    def delete(self, bucket: str, key: str) -> None:
        self._objects.pop((bucket, key), None)

    def list_objects(self) -> list[StoredObject]:
        return [
            StoredObject(bucket=bucket, key=key, content_type=content_type, size=len(payload))
            for (bucket, key), (payload, content_type) in self._objects.items()
        ]

    def clear(self) -> None:
        self._objects.clear()
