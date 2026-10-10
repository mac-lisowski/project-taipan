"""Fake adapter tests: roundtrip, stat fields, not-found, idempotent delete."""

import io

import pytest
from storage import FakeObjectStore, ObjectNotFound, StoredObject

BUCKET = "taipan"
CONTENT_TYPE = "application/pdf"


def _put(
    store: FakeObjectStore,
    key: str,
    payload: bytes,
) -> StoredObject:
    return store.put(BUCKET, key, io.BytesIO(payload), content_type=CONTENT_TYPE, size=len(payload))


def test_put_get_roundtrip_returns_same_bytes() -> None:
    store = FakeObjectStore()
    _put(store, "a/1", b"hello world")

    with store.get(BUCKET, "a/1") as (stream, _stat):
        assert stream.read() == b"hello world"


def test_get_reports_content_type_and_size() -> None:
    store = FakeObjectStore()
    payload = b"12345"
    _put(store, "a/2", payload)

    with store.get(BUCKET, "a/2") as (stream, stat):
        assert stat.content_type == CONTENT_TYPE
        assert stat.size == len(payload)
        assert stream.read() == payload


def test_put_returns_stored_object() -> None:
    store = FakeObjectStore()
    payload = b"abc"

    stored = _put(store, "a/3", payload)

    assert isinstance(stored, StoredObject)
    assert stored.bucket == BUCKET
    assert stored.size == len(payload)
    assert stored.content_type == CONTENT_TYPE


def test_get_missing_key_raises_object_not_found() -> None:
    store = FakeObjectStore()

    with pytest.raises(ObjectNotFound):
        store.get(BUCKET, "missing")


def test_delete_removes_object() -> None:
    store = FakeObjectStore()
    _put(store, "a/4", b"x")

    store.delete(BUCKET, "a/4")

    with pytest.raises(ObjectNotFound):
        store.get(BUCKET, "a/4")


def test_delete_missing_key_is_idempotent() -> None:
    store = FakeObjectStore()
    _put(store, "a/4", b"keep")

    store.delete(BUCKET, "never-there")
    store.delete(BUCKET, "never-there")

    with store.get(BUCKET, "a/4") as (stream, _stat):
        assert stream.read() == b"keep"


def test_list_objects_reports_captured_objects() -> None:
    store = FakeObjectStore()
    _put(store, "a/5", b"one")
    _put(store, "a/6", b"two")

    assert {obj.key for obj in store.list_objects()} == {"a/5", "a/6"}


def test_clear_empties_the_store() -> None:
    store = FakeObjectStore()
    _put(store, "a/7", b"gone")

    store.clear()

    assert store.list_objects() == []
