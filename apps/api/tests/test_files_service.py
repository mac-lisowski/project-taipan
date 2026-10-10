"""Files service tests: real session, FakeObjectStore, no HTTP.

Router mapping lives in test_files_http.py. This pins policy checks,
the object/row choreography, and the keyset listing.
"""

import hashlib
import io
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from api.authz import Principal
from api.files import service
from api.models import File, Role, User
from crypto import tenant_scope
from storage import FakeObjectStore

BUCKET = "taipan"


class _Upload:
    """Stand-in for FastAPI's UploadFile: the service reads only `.file`."""

    def __init__(self, data: bytes) -> None:
        self.file = io.BytesIO(data)


def _user(db, email: str = "user@x.com") -> User:
    user = User(email=email, hashed_password="not-a-hash")
    db.add(user)
    db.flush()
    return user


def _principal(user: User, tenant_id: str = "t1", roles: tuple[str, ...] = ()) -> Principal:
    return Principal(user_id=user.id, email=user.email, tenant_id=tenant_id, roles=roles)


def _seed(
    db,
    *,
    user_id: int,
    tenant_id: str = "t1",
    scope: str = "user",
    purpose="attachment",
    created_at: datetime | None = None,
):
    row = File(
        tenant_id=tenant_id,
        scope=scope,
        created_by_user_id=user_id,
        purpose=purpose,
        bucket=BUCKET,
        object_key=f"{purpose}s/{uuid.uuid4()}",
        filename="seed.bin",
        content_type="text/plain",
        size_bytes=1,
        sha256="a" * 64,
    )
    if created_at is not None:
        row.created_at = created_at
    # Tenant-carrying writes must flush inside the scope they point at.
    with tenant_scope(tenant_id):
        db.add(row)
        db.flush()
    return row


def _upload(db, store, user, **overrides) -> File:
    params = {
        "bucket": BUCKET,
        "tenant_id": "t1",
        "user_id": user.id,
        "purpose": "attachment",
        "scope": "user",
        "filename": "note.txt",
        "content_type": "text/plain",
    }
    params.update(overrides)
    return service.store_upload(db, store, **params)


@pytest.fixture
def db(session_factory):
    with session_factory() as session:
        yield session


@pytest.fixture
def store() -> FakeObjectStore:
    return FakeObjectStore()


def test_store_upload_writes_object_and_row(db, store):
    payload = b"hello world"
    row = _upload(db, store, _user(db), upload=_Upload(payload))
    objects = store.list_objects()
    assert len(objects) == 1
    assert objects[0].key == f"attachments/t1/{row.id}"
    assert objects[0].size == len(payload)
    assert row.object_key == objects[0].key
    assert row.sha256 == hashlib.sha256(payload).hexdigest()
    assert row.size_bytes == len(payload)
    assert (row.scope, row.purpose, row.bucket) == ("user", "attachment", BUCKET)
    assert db.get(File, row.id) is not None


def test_store_upload_over_cap_raises_too_large(db, store, monkeypatch):
    monkeypatch.setenv("API_FILES_MAX_BYTES", "4")
    with pytest.raises(service.TooLarge):
        _upload(db, store, _user(db), upload=_Upload(b"12345"))
    # The cap is enforced before the object is written.
    assert store.list_objects() == []


def test_store_upload_bad_mime_raises_unsupported_type(db, store):
    with pytest.raises(service.UnsupportedType):
        _upload(db, store, _user(db), content_type="application/x-msdownload", upload=_Upload(b"x"))
    assert store.list_objects() == []


def test_store_upload_unknown_purpose_raises_purpose_not_allowed(db, store):
    with pytest.raises(service.PurposeNotAllowed):
        _upload(db, store, _user(db), purpose="mystery", upload=_Upload(b"x"))


def test_store_upload_service_only_purpose_raises_purpose_not_allowed(db, store):
    # Artifact allows scope user, but no browser may mint one through POST.
    with pytest.raises(service.PurposeNotAllowed):
        _upload(db, store, _user(db), purpose="artifact", upload=_Upload(b"{}"))


def test_store_upload_forbidden_scope_raises_scope_not_allowed(db, store):
    # Artifact allows user scope only; tenant is refused.
    with pytest.raises(service.ScopeNotAllowed):
        _upload(db, store, _user(db), purpose="artifact", scope="tenant", upload=_Upload(b"{}"))


def test_store_bytes_writes_artifact_under_prefix(db, store):
    row = service.store_bytes(
        db,
        store,
        bucket=BUCKET,
        tenant_id="t1",
        user_id=_user(db).id,
        purpose="artifact",
        filename="report.json",
        content_type="application/json",
        data=b'{"ok": true}',
    )
    assert store.list_objects()[0].key == f"artifacts/t1/{row.id}"
    # The scope comes from the policy, not the caller.
    assert (row.scope, row.purpose) == ("user", "artifact")
    assert row.sha256 == hashlib.sha256(b'{"ok": true}').hexdigest()
    assert db.get(File, row.id) is not None


def test_store_bytes_commit_false_leaves_row_uncommitted(db, store, session_factory):
    row = service.store_bytes(
        db,
        store,
        bucket=BUCKET,
        tenant_id="t1",
        user_id=_user(db).id,
        purpose="artifact",
        filename="deferred.json",
        content_type="application/json",
        data=b"{}",
        commit=False,
    )
    assert row.id is not None
    assert len(store.list_objects()) == 1
    db.close()
    # The caller never committed, so a fresh session sees no row.
    with session_factory() as fresh:
        assert fresh.get(File, row.id) is None


def test_store_upload_failed_commit_compensates_object(db, store, monkeypatch):
    def _boom() -> None:
        raise RuntimeError("commit failed")

    monkeypatch.setattr(db, "commit", _boom)
    with pytest.raises(RuntimeError):
        _upload(db, store, _user(db), upload=_Upload(b"payload"))
    # The orphan object is removed when the row cannot land.
    assert store.list_objects() == []


def test_open_returns_same_bytes(db, store):
    payload = b"binary\x00payload"
    user = _user(db)
    row = _upload(db, store, user, upload=_Upload(payload))
    opened, content = service.open(db, store, row.id, principal=_principal(user))
    assert opened.id == row.id
    with content as (stream, stat):
        assert stream.read() == payload
        assert stat.size == len(payload)


def test_open_missing_object_raises_object_missing(db, store):
    user = _user(db)
    row = _upload(db, store, user, upload=_Upload(b"bytes"))
    store.clear()
    with pytest.raises(service.ObjectMissing):
        service.open(db, store, row.id, principal=_principal(user))


def test_open_other_users_private_file_raises_not_found(db, store):
    owner = _user(db, "own@x.com")
    stranger = _user(db, "stranger@x.com")
    row = _upload(db, store, owner, upload=_Upload(b"secret"))
    with pytest.raises(service.NotFound):
        service.open(db, store, row.id, principal=_principal(stranger))


def test_delete_removes_row_then_object(db, store):
    user = _user(db)
    row = _upload(db, store, user, upload=_Upload(b"bye"))
    service.delete(db, store, row.id, principal=_principal(user))
    assert db.get(File, row.id) is None
    assert store.list_objects() == []


def test_delete_twice_raises_not_found(db, store):
    user = _user(db)
    row = _upload(db, store, user, upload=_Upload(b"bye"))
    principal = _principal(user)
    service.delete(db, store, row.id, principal=principal)
    with pytest.raises(service.NotFound):
        service.delete(db, store, row.id, principal=principal)


def test_delete_tenant_file_needs_uploader_or_admin(db, store):
    uploader = _user(db, "uploader@x.com")
    admin = _user(db, "admin@x.com")
    member = _user(db, "member@x.com")
    row = _upload(db, store, uploader, scope="tenant", upload=_Upload(b"shared"))
    # A plain member of the tenant cannot delete someone else's shared file.
    with pytest.raises(service.NotFound):
        service.delete(db, store, row.id, principal=_principal(member))
    service.delete(db, store, row.id, principal=_principal(admin, roles=(Role.ADMIN,)))
    assert db.get(File, row.id) is None
    assert store.list_objects() == []


def test_list_page_pages_by_keyset(db):
    user = _user(db)
    base = datetime(2024, 1, 1, tzinfo=UTC)
    for i in range(5):
        _seed(db, user_id=user.id, created_at=base + timedelta(minutes=i))
    principal = _principal(user)
    first, cursor = service.list_page(db, principal=principal, limit=2)
    second, cursor = service.list_page(db, principal=principal, cursor=cursor, limit=2)
    third, cursor = service.list_page(db, principal=principal, cursor=cursor, limit=2)
    assert (len(first), len(second), len(third)) == (2, 2, 1)
    assert cursor is None
    assert len({row.id for row in [*first, *second, *third]}) == 5
    assert first[0].created_at > first[1].created_at


def test_list_page_filters_by_purpose_and_scope(db):
    owner = _user(db, "listowner@x.com")
    other = _user(db, "listother@x.com")
    _seed(db, user_id=owner.id)
    _seed(db, user_id=owner.id, scope="tenant")
    _seed(db, user_id=owner.id, purpose="artifact")
    # Another user's private file and another tenant's shared file stay hidden.
    _seed(db, user_id=other.id)
    _seed(db, user_id=other.id, tenant_id="t2", scope="tenant")
    principal = _principal(owner)
    everything, _ = service.list_page(db, principal=principal)
    assert len(everything) == 3
    artifacts, _ = service.list_page(db, principal=principal, purpose="artifact")
    assert [row.purpose for row in artifacts] == ["artifact"]
    shared, _ = service.list_page(db, principal=principal, scope="tenant")
    assert len(shared) == 1
    assert (shared[0].scope, shared[0].tenant_id) == ("tenant", "t1")
