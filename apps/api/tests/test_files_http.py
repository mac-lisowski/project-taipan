"""Files over HTTP: the five session-scoped /api/files routes.

The shared ``client`` fixture runs the real lifespan (a lazy S3ObjectStore);
each test swaps a FakeObjectStore onto ``app.state``, which the route reads
per request, so the swap wins.
"""

import uuid

from api import sessions
from api.config import get_config
from api.middleware import RequestSizeLimitMiddleware
from api.models import File, Role, User, UserTenant, UserTenantRole
from api_testsupport import admit_user, login, signin
from crypto import tenant_scope
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import select
from storage import FakeObjectStore

BUCKET = get_config().storage.s3_bucket


def _use_store(client) -> FakeObjectStore:
    fake = FakeObjectStore()
    client.app.state.object_store = fake
    return fake


def upload(client, data=b"hello", **fields):
    """POST a multipart upload; fields override purpose, scope, filename, content_type."""
    filename = fields.pop("filename", "note.txt")
    content_type = fields.pop("content_type", "text/plain")
    form = {"purpose": "attachment", "scope": "user", **fields}
    return client.post("/api/files", data=form, files={"file": (filename, data, content_type)})


def _ids(client, **params):
    return [row["id"] for row in client.get("/api/files", params=params).json()["files"]]


def _scope_of(session_factory, email):
    with session_factory() as db:
        user_id = db.scalar(select(User.id).where(User.email == email))
        tenant_id = db.scalar(select(UserTenant.tenant_id).where(UserTenant.user_id == user_id))
    return user_id, tenant_id


def _join_tenant(session_factory, email, tenant_id, *, role=None):
    """Add a second member to an existing tenant; returns the new user id."""
    with session_factory() as db:
        user = User(email=email, hashed_password="x")
        db.add(user)
        db.flush()
        with tenant_scope(tenant_id):
            db.add(UserTenant(user_id=user.id, tenant_id=tenant_id))
            if role is not None:
                db.add(UserTenantRole(user_id=user.id, tenant_id=tenant_id, role=role))
            db.flush()
        db.commit()
        return user.id


def _mint(client, user_id, tenant_id):
    client.cookies.set(sessions.COOKIE_NAME, sessions.mint(user_id, tenant_id))


def _seed_artifact(session_factory, user_id, tenant_id):
    row = File(
        tenant_id=tenant_id,
        scope="user",
        created_by_user_id=user_id,
        purpose="artifact",
        bucket=BUCKET,
        object_key=f"artifacts/{uuid.uuid4()}",
        filename="seed.txt",
        content_type="text/plain",
        size_bytes=1,
        sha256="a" * 64,
    )
    with session_factory() as db:
        with tenant_scope(tenant_id):
            db.add(row)
            db.flush()
        db.commit()
    return str(row.id)


def test_upload_returns_metadata_and_writes_object_and_row(client, session_factory):
    store = _use_store(client)
    signin(client, "uploader@x.com")
    payload = b"hello world"

    resp = upload(client, payload)

    assert resp.status_code == 201
    body = resp.json()
    assert len(body) == 8
    assert {"id", "purpose", "scope", "filename", "size_bytes", "sha256"} <= set(body)
    assert (body["purpose"], body["scope"], body["filename"]) == ("attachment", "user", "note.txt")
    assert body["size_bytes"] == len(payload) and len(body["sha256"]) == 64
    objects = store.list_objects()
    assert len(objects) == 1 and objects[0].size == len(payload)
    with session_factory() as db:
        row = db.get(File, uuid.UUID(body["id"]))
    assert row is not None and row.object_key == objects[0].key


def test_upload_over_cap_is_413(client, monkeypatch):
    store = _use_store(client)
    monkeypatch.setenv("API_FILES_MAX_BYTES", "16")
    signin(client, "big@x.com")

    resp = upload(client, b"x" * 100)

    assert resp.status_code == 413
    # The object is never written when the body is refused.
    assert store.list_objects() == []


def test_upload_bad_mime_is_415(client):
    _use_store(client)
    signin(client, "mime@x.com")

    assert upload(client, b"x", content_type="application/x-msdownload").status_code == 415


def test_upload_purpose_and_scope_errors_are_400(client):
    _use_store(client)
    signin(client, "policy@x.com")

    # Unknown purpose, service-only purpose, and a scope the purpose forbids.
    assert upload(client, b"x", purpose="mystery").status_code == 400
    assert (
        upload(client, b"{}", purpose="artifact", content_type="application/json").status_code
        == 400
    )
    forbidden = upload(
        client, b"{}", purpose="artifact", scope="tenant", content_type="application/json"
    )
    assert forbidden.status_code == 400


def test_list_is_scoped_to_principal(client):
    _use_store(client)
    admit_user(client, "alice@x.com")
    admit_user(client, "bob@x.com")
    login(client, "alice@x.com")
    alice_private = upload(client, b"alice-private").json()["id"]
    upload(client, b"alice-shared", scope="tenant")
    login(client, "bob@x.com")

    # Bob shares no tenant with Alice, so he sees neither her private nor her tenant file.
    assert _ids(client) == []
    assert client.get(f"/api/files/{alice_private}").status_code == 404
    bob_private = upload(client, b"bob-private").json()["id"]
    assert _ids(client) == [bob_private]


def test_same_tenant_member_reads_tenant_file(client, session_factory):
    store = _use_store(client)
    signin(client, "owner@x.com")
    private = upload(client, b"private").json()["id"]
    shared = upload(client, b"shared", scope="tenant").json()["id"]
    _user_id, tenant_id = _scope_of(session_factory, "owner@x.com")
    member_id = _join_tenant(session_factory, "member@x.com", tenant_id)
    _mint(client, member_id, tenant_id)

    assert _ids(client) == [shared]
    assert client.get(f"/api/files/{shared}/content").content == b"shared"
    assert client.get(f"/api/files/{private}").status_code == 404
    # A plain member is neither the uploader nor an admin, so delete stays hidden.
    assert client.delete(f"/api/files/{shared}").status_code == 404
    assert len(store.list_objects()) == 2


def test_list_pages_newest_first_by_keyset(client):
    _use_store(client)
    signin(client, "pager@x.com")
    made = [upload(client, f"p{i}".encode()).json()["id"] for i in range(3)]

    first = client.get("/api/files", params={"limit": 2}).json()
    assert [row["id"] for row in first["files"]] == made[::-1][:2]
    assert first["next_cursor"] is not None

    second = client.get("/api/files", params={"limit": 2, "cursor": first["next_cursor"]}).json()
    assert [row["id"] for row in second["files"]] == made[::-1][2:]
    assert second["next_cursor"] is None


def test_list_filters_by_purpose_and_scope(client, session_factory):
    _use_store(client)
    signin(client, "filter@x.com")
    upload(client, b"a")
    tenant_file = upload(client, b"t", scope="tenant").json()["id"]
    user_id, tenant_id = _scope_of(session_factory, "filter@x.com")
    artifact = _seed_artifact(session_factory, user_id, tenant_id)

    assert len(_ids(client)) == 3
    assert _ids(client, purpose="artifact") == [artifact]
    assert _ids(client, scope="tenant") == [tenant_file]


def test_broken_cursor_is_400(client):
    _use_store(client)
    signin(client, "cursor@x.com")

    assert client.get("/api/files", params={"cursor": "garbage"}).status_code == 400


def test_content_streams_bytes_with_pinned_headers(client):
    _use_store(client)
    signin(client, "content@x.com")
    payload = b"\x00\x01binary payload"
    made = upload(client, payload, filename="blob.pdf", content_type="application/pdf").json()

    resp = client.get(f"/api/files/{made['id']}/content")

    assert resp.status_code == 200
    assert resp.content == payload
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.headers["content-length"] == str(len(payload))
    assert resp.headers["content-disposition"].startswith("attachment")
    assert "blob.pdf" in resp.headers["content-disposition"]
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["cache-control"] == "private"


def test_content_image_is_inline(client):
    _use_store(client)
    signin(client, "image@x.com")
    made = upload(client, b"\x89PNG", filename="pic.png", content_type="image/png").json()

    resp = client.get(f"/api/files/{made['id']}/content")

    assert resp.headers["content-disposition"].startswith("inline")
    assert "pic.png" in resp.headers["content-disposition"]


def test_content_missing_object_is_404(client):
    store = _use_store(client)
    signin(client, "gone@x.com")
    made = upload(client, b"bytes").json()
    store.clear()

    assert client.get(f"/api/files/{made['id']}/content").status_code == 404


def test_delete_removes_row_and_object(client, session_factory):
    store = _use_store(client)
    signin(client, "deleter@x.com")
    made = upload(client, b"bye").json()

    assert client.delete(f"/api/files/{made['id']}").status_code == 204
    assert store.list_objects() == []
    with session_factory() as db:
        assert db.get(File, uuid.UUID(made["id"])) is None


def test_delete_other_users_private_is_404(client):
    store = _use_store(client)
    admit_user(client, "owner2@x.com")
    admit_user(client, "stranger@x.com")
    login(client, "owner2@x.com")
    made = upload(client, b"secret").json()
    login(client, "stranger@x.com")

    assert client.delete(f"/api/files/{made['id']}").status_code == 404
    # A refused delete leaves the object in place.
    assert len(store.list_objects()) == 1


def test_tenant_admin_deletes_tenant_file(client, session_factory):
    store = _use_store(client)
    signin(client, "owner3@x.com")
    made = upload(client, b"shared", scope="tenant").json()["id"]
    _user_id, tenant_id = _scope_of(session_factory, "owner3@x.com")
    admin_id = _join_tenant(session_factory, "admin3@x.com", tenant_id, role=Role.ADMIN)
    _mint(client, admin_id, tenant_id)

    assert client.delete(f"/api/files/{made}").status_code == 204
    assert store.list_objects() == []


def test_size_bound_counts_receive_bytes_without_content_length(monkeypatch):
    monkeypatch.setenv("API_FILES_MAX_BYTES", "16")
    app = FastAPI()
    app.add_middleware(RequestSizeLimitMiddleware)

    @app.post("/api/files")
    async def echo(request: Request) -> dict[str, object]:
        return {"length": len(await request.body()), "cl": request.headers.get("content-length")}

    client = TestClient(app)
    # A chunked body carries no Content-Length for the middleware to trust.
    over = client.post("/api/files", content=iter([b"x" * 20000]))
    assert over.status_code == 413
    under = client.post("/api/files", content=iter([b"x" * 10]))
    assert under.status_code == 200
    assert under.json() == {"length": 10, "cl": None}
