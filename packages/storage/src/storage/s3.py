"""S3 adapter: wraps the minio SDK. The client is built lazily."""

from __future__ import annotations

from typing import BinaryIO
from urllib.parse import urlparse

from minio import Minio
from minio.error import S3Error

from storage.ports import (
    ObjectContent,
    ObjectNotFound,
    ObjectStat,
    ObjectStore,
    StorageError,
    StoredObject,
)


def _parse_endpoint(endpoint: str) -> tuple[str, bool]:
    """Split an endpoint URL into a minio host and a ``secure`` flag."""
    parsed = urlparse(endpoint)
    if not parsed.scheme or not parsed.netloc:
        raise StorageError(f"invalid S3 endpoint: {endpoint!r}")
    return parsed.netloc, parsed.scheme == "https"


def _map_error(exc: S3Error) -> StorageError:
    if exc.code == "NoSuchKey":
        return ObjectNotFound(str(exc))
    return StorageError(str(exc))


class S3ObjectStore(ObjectStore):
    """ObjectStore over any S3-compatible server via the minio SDK."""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        *,
        region: str | None = None,
    ) -> None:
        self._host, self._secure = _parse_endpoint(endpoint)
        self._access_key = access_key
        self._secret_key = secret_key
        self._region = region
        self._client: Minio | None = None
        self._ensured_buckets: set[str] = set()

    def _minio(self) -> Minio:
        # Lazy: boot without MinIO must not fail until the first call.
        if self._client is None:
            self._client = Minio(
                self._host,
                access_key=self._access_key,
                secret_key=self._secret_key,
                secure=self._secure,
                region=self._region,
            )
        return self._client

    def ensure_bucket(self, bucket: str) -> None:
        """Create the bucket, tolerating one that already exists."""
        try:
            self._minio().make_bucket(bucket)
        except S3Error as exc:
            if exc.code in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                return
            raise _map_error(exc) from exc

    def _ensure_bucket_once(self, bucket: str) -> None:
        if bucket in self._ensured_buckets:
            return
        self.ensure_bucket(bucket)
        self._ensured_buckets.add(bucket)

    def put(
        self,
        bucket: str,
        key: str,
        data: BinaryIO,
        *,
        content_type: str,
        size: int,
    ) -> StoredObject:
        self._ensure_bucket_once(bucket)
        try:
            self._minio().put_object(bucket, key, data, length=size, content_type=content_type)
        except S3Error as exc:
            raise _map_error(exc) from exc
        return StoredObject(bucket=bucket, key=key, content_type=content_type, size=size)

    def get(self, bucket: str, key: str) -> ObjectContent:
        client = self._minio()
        try:
            meta = client.stat_object(bucket, key)
            response = client.get_object(bucket, key)
        except S3Error as exc:
            raise _map_error(exc) from exc
        stat = ObjectStat(
            content_type=meta.content_type or "application/octet-stream",
            size=int(meta.size or 0),
        )
        return ObjectContent(response, stat)

    def delete(self, bucket: str, key: str) -> None:
        try:
            self._minio().remove_object(bucket, key)
        except S3Error as exc:
            raise _map_error(exc) from exc
