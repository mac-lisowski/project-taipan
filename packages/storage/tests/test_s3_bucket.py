"""S3ObjectStore creates the bucket once per bucket before the first put."""

import io
from collections.abc import Iterator

import pytest
import storage.s3 as s3_module
from minio.error import S3Error
from storage import S3ObjectStore, StorageError

# Instances built by the minio stand-in; cleared per test.
_built: list["_StubMinio"] = []


class _StubMinio:
    """Stands in for minio.Minio and records bucket creates and puts."""

    def __init__(self, endpoint: str, **kwargs: object) -> None:
        self.buckets_made: list[str] = []
        self.puts: list[dict[str, object]] = []
        _built.append(self)

    def make_bucket(self, bucket: str) -> None:
        self.buckets_made.append(bucket)

    def put_object(
        self,
        bucket: str,
        key: str,
        data: object,
        length: int,
        content_type: str = "application/octet-stream",
    ) -> None:
        self.puts.append({"bucket": bucket, "key": key})


def _error_minio(code: str) -> type:
    """A minio stand-in whose make_bucket raises the given S3 error code."""

    class _Minio(_StubMinio):
        def make_bucket(self, bucket: str) -> None:
            raise S3Error("resp", code, "boom", "b", "req", "host", bucket, "")

    return _Minio


@pytest.fixture(autouse=True)
def _reset_built() -> Iterator[None]:
    _built.clear()
    yield
    _built.clear()


def _store(monkeypatch: pytest.MonkeyPatch, factory: type = _StubMinio) -> S3ObjectStore:
    monkeypatch.setattr(s3_module, "Minio", factory)
    return S3ObjectStore("http://localhost:9000", "key", "secret")


def _put(store: S3ObjectStore, bucket: str, key: str) -> None:
    store.put(bucket, key, io.BytesIO(b"hi"), content_type="text/plain", size=2)


def test_put_creates_bucket_once_across_two_puts(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _store(monkeypatch)

    _put(store, "b", "k1")
    _put(store, "b", "k2")

    [client] = _built
    assert client.buckets_made == ["b"]


def test_second_bucket_triggers_its_own_make_bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _store(monkeypatch)

    _put(store, "b1", "k")
    _put(store, "b2", "k")

    [client] = _built
    assert client.buckets_made == ["b1", "b2"]


@pytest.mark.parametrize("code", ["BucketAlreadyOwnedByYou", "BucketAlreadyExists"])
def test_existing_bucket_error_is_swallowed(monkeypatch: pytest.MonkeyPatch, code: str) -> None:
    store = _store(monkeypatch, _error_minio(code))

    _put(store, "b", "k")

    [client] = _built
    assert len(client.puts) == 1  # the put still went through


def test_other_s3_error_maps_to_storage_error(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _store(monkeypatch, _error_minio("AccessDenied"))

    with pytest.raises(StorageError):
        _put(store, "b", "k")

    [client] = _built
    assert client.puts == []  # the failure short-circuits before put_object
