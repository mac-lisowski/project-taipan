"""S3ObjectStore construction is lazy: no client, no socket."""

import io
import socket
from collections.abc import Iterator

import pytest
import storage.s3 as s3_module
from minio.error import S3Error
from storage import ObjectNotFound, S3ObjectStore, StorageError

# Constructor calls recorded by the minio stand-in; cleared per test.
_built: list["_RecordingMinio"] = []


class _RecordingMinio:
    """Stands in for minio.Minio and records constructor args and calls."""

    def __init__(self, endpoint: str, **kwargs: object) -> None:
        self.endpoint = endpoint
        self.kwargs = kwargs
        self.puts: list[dict[str, object]] = []
        _built.append(self)

    def make_bucket(self, bucket: str) -> None:
        pass

    def put_object(
        self,
        bucket: str,
        key: str,
        data: object,
        length: int,
        content_type: str = "application/octet-stream",
    ) -> None:
        self.puts.append(
            {"bucket": bucket, "key": key, "length": length, "content_type": content_type}
        )


def _error_minio(code: str) -> type:
    """A minio stand-in whose stat_object raises the given S3 error code."""

    class _Minio:
        def __init__(self, endpoint: str, **kwargs: object) -> None:
            pass

        def stat_object(self, *args: object, **kwargs: object) -> None:
            raise S3Error("resp", code, "boom", "b", "req", "host", "bucket", "key")

    return _Minio


@pytest.fixture(autouse=True)
def _reset_built() -> Iterator[None]:
    _built.clear()
    yield
    _built.clear()


def test_construction_opens_no_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail(*args: object, **kwargs: object) -> None:
        raise AssertionError("S3ObjectStore construction opened a socket")

    monkeypatch.setattr(socket, "socket", _fail)

    store = S3ObjectStore("http://127.0.0.1:9", "key", "secret")

    assert store is not None


def test_construction_builds_no_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(s3_module, "Minio", _RecordingMinio)

    S3ObjectStore("http://127.0.0.1:9", "key", "secret")

    assert _built == []


def test_http_endpoint_is_insecure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(s3_module, "Minio", _RecordingMinio)
    store = S3ObjectStore("http://localhost:9000", "key", "secret")

    store.put("b", "k", io.BytesIO(b"hi"), content_type="text/plain", size=2)

    [client] = _built
    assert client.endpoint == "localhost:9000"
    assert client.kwargs["secure"] is False


def test_https_endpoint_is_secure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(s3_module, "Minio", _RecordingMinio)
    store = S3ObjectStore("https://minio.example.com:9000", "key", "secret")

    store.put("b", "k", io.BytesIO(b"hi"), content_type="text/plain", size=2)

    [client] = _built
    assert client.endpoint == "minio.example.com:9000"
    assert client.kwargs["secure"] is True


def test_put_passes_length_and_content_type_to_minio(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(s3_module, "Minio", _RecordingMinio)
    store = S3ObjectStore("http://localhost:9000", "key", "secret")

    store.put("b", "k", io.BytesIO(b"hello"), content_type="text/plain", size=5)

    [client] = _built
    [call] = client.puts
    assert call["length"] == 5
    assert call["content_type"] == "text/plain"


def test_missing_object_error_maps_to_object_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(s3_module, "Minio", _error_minio("NoSuchKey"))
    store = S3ObjectStore("http://localhost:9000", "key", "secret")

    with pytest.raises(ObjectNotFound):
        store.get("b", "k")


def test_other_s3_error_maps_to_storage_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(s3_module, "Minio", _error_minio("AccessDenied"))
    store = S3ObjectStore("http://localhost:9000", "key", "secret")

    with pytest.raises(StorageError) as excinfo:
        store.get("b", "k")

    assert not isinstance(excinfo.value, ObjectNotFound)
