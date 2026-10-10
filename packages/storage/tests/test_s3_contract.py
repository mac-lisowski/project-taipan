"""One contract module: FakeObjectStore always, S3ObjectStore when MinIO is up.

The S3 leg runs only when the configured endpoint accepts a socket, and
skips cleanly otherwise, the same convention as the Postgres tests.
Credentials come from ``API_TEST_S3_*`` env vars with the config defaults.
"""

import io
import os
import socket
import uuid
from urllib.parse import urlparse

import pytest
from storage import FakeObjectStore, ObjectNotFound, ObjectStore, S3ObjectStore

ENDPOINT = os.environ.get("API_TEST_S3_ENDPOINT", "http://localhost:9000")
ACCESS_KEY = os.environ.get("API_TEST_S3_ACCESS_KEY", "taipan")
SECRET_KEY = os.environ.get("API_TEST_S3_SECRET_KEY", "taipan-dev-secret")
BUCKET = os.environ.get("API_TEST_S3_BUCKET", "taipan")

CONTENT_TYPE = "text/plain"


def _endpoint_reachable(endpoint: str) -> bool:
    parsed = urlparse(endpoint)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


@pytest.fixture(params=["fake", "s3"])
def store(request: pytest.FixtureRequest) -> ObjectStore:
    if request.param == "fake":
        yield FakeObjectStore()
        return
    if not _endpoint_reachable(ENDPOINT):
        pytest.skip(f"MinIO unreachable at {ENDPOINT}; S3 leg skipped")
    yield S3ObjectStore(ENDPOINT, ACCESS_KEY, SECRET_KEY)


def _key() -> str:
    # A fresh key per test keeps the shared bucket free of collisions.
    return f"contract/{uuid.uuid4().hex}"


def _put(store: ObjectStore, key: str, payload: bytes) -> None:
    store.put(BUCKET, key, io.BytesIO(payload), content_type=CONTENT_TYPE, size=len(payload))


def test_roundtrip_returns_same_bytes(store: ObjectStore) -> None:
    key = _key()
    payload = b"contract bytes"

    _put(store, key, payload)

    with store.get(BUCKET, key) as (stream, _stat):
        assert stream.read() == payload
    store.delete(BUCKET, key)


def test_stat_carries_content_type_and_size(store: ObjectStore) -> None:
    key = _key()
    payload = b"1234567"

    _put(store, key, payload)

    with store.get(BUCKET, key) as (_stream, stat):
        assert stat.content_type == CONTENT_TYPE
        assert stat.size == len(payload)
    store.delete(BUCKET, key)


def test_get_missing_key_raises_object_not_found(store: ObjectStore) -> None:
    with pytest.raises(ObjectNotFound):
        store.get(BUCKET, _key())


def test_delete_removes_object_and_is_idempotent(store: ObjectStore) -> None:
    key = _key()
    _put(store, key, b"gone")

    store.delete(BUCKET, key)
    store.delete(BUCKET, key)

    with pytest.raises(ObjectNotFound):
        store.get(BUCKET, key)
