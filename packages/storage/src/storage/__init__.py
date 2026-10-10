"""Object storage seam: one store port, S3 and fake adapters."""

from storage.fake import FakeObjectStore
from storage.ports import (
    ObjectContent,
    ObjectNotFound,
    ObjectStore,
    StorageError,
    StoredObject,
)
from storage.s3 import S3ObjectStore

__all__ = [
    "FakeObjectStore",
    "ObjectContent",
    "ObjectNotFound",
    "ObjectStore",
    "S3ObjectStore",
    "StorageError",
    "StoredObject",
]
