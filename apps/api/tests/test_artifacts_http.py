"""Artifacts over HTTP: the four session-scoped /api/artifacts routes.

No POST exists (the save_artifact tool path lands separately); tests seed
through ``api.artifacts.service`` against the same FakeObjectStore the
routes read through ``get_object_store``.
"""

import uuid
from datetime import UTC, datetime

from api import artifacts
from api.authz import Principal
from api.config import get_config
from api.models import ChatArtifact, ChatThread, File, User, UserTenant
from api_testsupport import admit_user, login, signin
from crypto import tenant_scope
from sqlalchemy import select
from storage import FakeObjectStore

BUCKET = get_config().storage.s3_bucket
DOC = {"markdown": "# Report\n\nbody"}
ROWS = {"rows": [{"a": 1}, {"a": 2}]}
SUMMARY_KEYS = {"id", "title", "type", "threadId", "updatedAt"}


def _use_store(client) -> FakeObjectStore:
    fake = FakeObjectStore()
    client.app.state.object_store = fake
    return fake


def _scope_of(session_factory, email):
    with session_factory() as db:
        user_id = db.scalar(select(User.id).where(User.email == email))
        tenant_id = db.scalar(select(UserTenant.tenant_id).where(UserTenant.user_id == user_id))
    return user_id, tenant_id


def _seed(
    client,
    session_factory,
    email,
    *,
    title="doc",
    type="taipan_document",
    content=None,
    thread_id=None,
) -> str:
    """Persist an artifact for the user's personal tenant via the service."""
    user_id, tenant_id = _scope_of(session_factory, email)
    principal = Principal(user_id=user_id, email=email, tenant_id=tenant_id, roles=())
    with session_factory() as db:
        row = artifacts.create(
            db,
            client.app.state.object_store,
            bucket=BUCKET,
            principal=principal,
            type=type,
            title=title,
            content=DOC if content is None else content,
            thread_id=thread_id,
        )
        return str(row.id)


def _seed_thread(session_factory, email) -> str:
    user_id, tenant_id = _scope_of(session_factory, email)
    with session_factory() as db:
        with tenant_scope(tenant_id):
            thread = ChatThread(user_id=user_id, tenant_id=tenant_id, title="t")
            db.add(thread)
            db.flush()
        db.commit()
        return str(thread.id)


def _stamp_updates(session_factory, ids):
    """Pin distinct updated_at values so the keyset order is deterministic."""
    with session_factory() as db:
        rows = [db.get(ChatArtifact, uuid.UUID(artifact_id)) for artifact_id in ids]
        # The guard requires the flush inside each row's tenant scope.
        for i, row in enumerate(rows):
            with tenant_scope(row.tenant_id):
                row.updated_at = datetime(2024, 1, i + 1, tzinfo=UTC)
                db.flush()
        db.commit()


def test_list_returns_sdk_summary_shape(client, session_factory):
    _use_store(client)
    signin(client, "list@x.com")
    _seed(client, session_factory, "list@x.com", title="alpha")

    resp = client.get("/api/artifacts")

    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"artifacts", "nextCursor"}
    assert body["nextCursor"] is None
    (item,) = body["artifacts"]
    assert set(item) == SUMMARY_KEYS
    assert (item["title"], item["type"]) == ("alpha", "taipan_document")
    assert item["threadId"] == ""
    assert isinstance(item["updatedAt"], float)


def test_list_pages_newest_first_by_keyset(client, session_factory):
    _use_store(client)
    signin(client, "pager@x.com")
    made = [_seed(client, session_factory, "pager@x.com", title=f"a{i}") for i in range(3)]
    _stamp_updates(session_factory, made)

    first = client.get("/api/artifacts", params={"limit": 2}).json()
    assert [a["id"] for a in first["artifacts"]] == made[::-1][:2]
    assert first["nextCursor"] is not None

    second = client.get("/api/artifacts", params={"limit": 2, "cursor": first["nextCursor"]}).json()
    assert [a["id"] for a in second["artifacts"]] == made[::-1][2:]
    assert second["nextCursor"] is None


def test_list_filters_by_name_and_repeatable_type(client, session_factory):
    _use_store(client)
    signin(client, "filter@x.com")
    _seed(client, session_factory, "filter@x.com", title="Quarterly Report")
    _seed(client, session_factory, "filter@x.com", title="Meeting notes")
    table = _seed(
        client,
        session_factory,
        "filter@x.com",
        title="Q table",
        type="taipan_table",
        content=ROWS,
    )

    by_name = client.get("/api/artifacts", params={"name": "report"}).json()
    assert [a["title"] for a in by_name["artifacts"]] == ["Quarterly Report"]

    by_type = client.get("/api/artifacts", params=[("type", "taipan_table")]).json()
    assert [a["id"] for a in by_type["artifacts"]] == [table]

    both = client.get(
        "/api/artifacts", params=[("type", "taipan_document"), ("type", "taipan_table")]
    ).json()
    assert len(both["artifacts"]) == 3

    assert client.get("/api/artifacts", params={"type": "bogus"}).json()["artifacts"] == []


def test_list_rejects_broken_cursor(client):
    _use_store(client)
    signin(client, "cursor@x.com")
    assert client.get("/api/artifacts", params={"cursor": "garbage"}).status_code == 400


def test_get_returns_summary_plus_parsed_content(client, session_factory):
    _use_store(client)
    signin(client, "reader@x.com")
    aid = _seed(client, session_factory, "reader@x.com", type="taipan_table", content=ROWS)

    resp = client.get(f"/api/artifacts/{aid}")

    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == SUMMARY_KEYS | {"content"}
    assert body["id"] == aid
    assert body["content"] == ROWS


def test_get_missing_object_is_404(client, session_factory):
    store = _use_store(client)
    signin(client, "gone@x.com")
    aid = _seed(client, session_factory, "gone@x.com")
    store.clear()

    assert client.get(f"/api/artifacts/{aid}").status_code == 404


def test_patch_swaps_content_and_bumps_version(client, session_factory):
    store = _use_store(client)
    signin(client, "editor@x.com")
    aid = _seed(client, session_factory, "editor@x.com", content={"markdown": "v1"})

    resp = client.patch(f"/api/artifacts/{aid}", json={"content": {"markdown": "v2"}})

    assert resp.status_code == 200
    assert set(resp.json()) == SUMMARY_KEYS
    got = client.get(f"/api/artifacts/{aid}").json()
    assert got["content"] == {"markdown": "v2"}
    with session_factory() as db:
        assert db.get(ChatArtifact, uuid.UUID(aid)).version == 2
    # The update swapped file rows and dropped the old object.
    assert len(store.list_objects()) == 1


def test_patch_without_content_is_422(client, session_factory):
    _use_store(client)
    signin(client, "bad@x.com")
    aid = _seed(client, session_factory, "bad@x.com")

    assert client.patch(f"/api/artifacts/{aid}", json={}).status_code == 422


def test_delete_removes_row_file_and_object(client, session_factory):
    store = _use_store(client)
    signin(client, "del@x.com")
    aid = _seed(client, session_factory, "del@x.com")
    with session_factory() as db:
        file_id = db.get(ChatArtifact, uuid.UUID(aid)).file_id

    assert client.delete(f"/api/artifacts/{aid}").status_code == 204
    assert client.get(f"/api/artifacts/{aid}").status_code == 404
    with session_factory() as db:
        assert db.get(ChatArtifact, uuid.UUID(aid)) is None
        assert db.get(File, file_id) is None
    assert store.list_objects() == []


def test_other_users_artifacts_404_everywhere(client, session_factory):
    store = _use_store(client)
    admit_user(client, "owner@x.com")
    admit_user(client, "stranger@x.com")
    login(client, "owner@x.com")
    aid = _seed(client, session_factory, "owner@x.com")

    login(client, "stranger@x.com")
    assert client.get("/api/artifacts").json()["artifacts"] == []
    assert client.get(f"/api/artifacts/{aid}").status_code == 404
    assert (
        client.patch(f"/api/artifacts/{aid}", json={"content": {"markdown": "x"}}).status_code
        == 404
    )
    assert client.delete(f"/api/artifacts/{aid}").status_code == 404
    # The refused writes and deletes left the object in place.
    assert len(store.list_objects()) == 1


def test_threadid_empties_when_thread_is_deleted(client, session_factory):
    _use_store(client)
    signin(client, "survivor@x.com")
    tid = _seed_thread(session_factory, "survivor@x.com")
    aid = _seed(client, session_factory, "survivor@x.com", thread_id=uuid.UUID(tid))

    assert client.get(f"/api/artifacts/{aid}").json()["threadId"] == tid
    assert client.delete(f"/api/threads/delete/{tid}").status_code == 204
    assert client.get(f"/api/artifacts/{aid}").json()["threadId"] == ""


def test_routes_require_a_session(client):
    _use_store(client)
    assert client.get("/api/artifacts").status_code == 401


def test_generic_files_delete_on_an_artifact_file_is_409(client, session_factory):
    signin(client, "guard@x.com")
    artifact_id = _seed(client, session_factory, "guard@x.com")
    with session_factory() as db:
        file_id = db.scalar(
            select(ChatArtifact.file_id).where(ChatArtifact.id == uuid.UUID(artifact_id))
        )

    resp = client.delete(f"/api/files/{file_id}")

    assert resp.status_code == 409
    assert client.get(f"/api/artifacts/{artifact_id}").status_code == 200
