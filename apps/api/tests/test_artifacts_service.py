"""Artifacts service tests: real session, FakeObjectStore, no HTTP.

This pins the row+file+object choreography, the keyset listing, and the
user-delete ordering contract: purge_user must run before files
detach_user or RESTRICT on chat_artifacts.file_id blocks the purge.
"""

import io
from typing import Any

import pytest
from api import users
from api.artifacts import service
from api.authz import Principal
from api.models import ChatArtifact, ChatThread, File, User
from crypto import tenant_scope
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from storage import FakeObjectStore

BUCKET = "taipan"
DOC = {"markdown": "# Report\n\nbody"}
ROWS = {"rows": [{"a": 1}]}


def _user(db, email="u@x.com") -> User:
    user = User(email=email, hashed_password="x")
    db.add(user)
    db.flush()
    return user


def _principal(user: User, tenant_id: str = "t1") -> Principal:
    return Principal(user_id=user.id, email=user.email, tenant_id=tenant_id, roles=())


def _create(db, store, user: User, **overrides) -> ChatArtifact:
    params: dict[str, Any] = {
        "bucket": BUCKET,
        "principal": _principal(user),
        "type": "taipan_document",
        "title": "doc",
        "content": DOC,
    }
    params.update(overrides)
    return service.create(db, store, **params)


def _keys(store) -> set[str]:
    return {obj.key for obj in store.list_objects()}


def _put(store, key: str) -> None:
    store.put(BUCKET, key, io.BytesIO(b"x"), content_type="application/json", size=1)


@pytest.fixture
def db(session_factory):
    with session_factory() as session:
        yield session


@pytest.fixture
def store() -> FakeObjectStore:
    return FakeObjectStore()


def test_create_lands_artifact_file_row_and_object(db, store):
    user = _user(db)
    row = _create(db, store, user, title="Q3 report", type="taipan_document")
    art = db.get(ChatArtifact, row.id)
    assert art is not None
    assert (art.type, art.title, art.version, art.user_id, art.tenant_id) == (
        "taipan_document",
        "Q3 report",
        1,
        user.id,
        "t1",
    )
    assert art.thread_id is None
    file_row = db.get(File, art.file_id)
    assert file_row is not None
    assert (file_row.purpose, file_row.scope, file_row.created_by_user_id) == (
        "artifact",
        "user",
        user.id,
    )
    assert file_row.object_key == f"artifacts/t1/{file_row.id}"
    assert _keys(store) == {file_row.object_key}
    _, content = service.get(db, store, art.id, principal=_principal(user))
    assert content == DOC


def test_get_other_users_artifact_raises_not_found(db, store):
    owner = _user(db, "own@x.com")
    stranger = _user(db, "str@x.com")
    row = _create(db, store, owner)
    with pytest.raises(service.NotFound):
        service.get(db, store, row.id, principal=_principal(stranger))


def test_get_missing_object_raises_object_missing(db, store):
    user = _user(db)
    row = _create(db, store, user)
    store.clear()
    with pytest.raises(service.ObjectMissing):
        service.get(db, store, row.id, principal=_principal(user))


def test_list_page_keysets_on_updated_at(db, store):
    user = _user(db)
    for i in range(5):
        _create(db, store, user, title=f"doc{i}")
    principal = _principal(user)
    first, cursor = service.list_page(db, principal=principal, limit=2)
    second, cursor = service.list_page(db, principal=principal, cursor=cursor, limit=2)
    third, cursor = service.list_page(db, principal=principal, cursor=cursor, limit=2)
    assert (len(first), len(second), len(third)) == (2, 2, 1)
    assert cursor is None
    assert len({a.id for a in [*first, *second, *third]}) == 5
    assert first[0].updated_at >= first[1].updated_at


def test_list_page_name_filter_matches_title_case_insensitive(db, store):
    user = _user(db)
    _create(db, store, user, title="Quarterly Report")
    _create(db, store, user, title="Meeting notes")
    rows, _ = service.list_page(db, principal=_principal(user), name="report")
    assert [a.title for a in rows] == ["Quarterly Report"]


def test_list_page_name_filter_escapes_wildcards(db, store):
    user = _user(db)
    _create(db, store, user, title="100% done")
    _create(db, store, user, title="1000 steps")
    rows, _ = service.list_page(db, principal=_principal(user), name="100%")
    # A bare % must not act as a LIKE wildcard.
    assert [a.title for a in rows] == ["100% done"]


def test_list_page_type_filter_is_repeatable(db, store):
    user = _user(db)
    _create(db, store, user, type="taipan_document", title="d")
    _create(db, store, user, type="taipan_table", title="t", content=ROWS)
    _create(db, store, user, type="taipan_other", title="o")
    both, _ = service.list_page(
        db, principal=_principal(user), types=["taipan_document", "taipan_table"]
    )
    assert sorted(a.title for a in both) == ["d", "t"]
    tables, _ = service.list_page(db, principal=_principal(user), types=["taipan_table"])
    assert [a.title for a in tables] == ["t"]


def test_list_page_is_owner_scoped(db, store):
    owner = _user(db, "o@x.com")
    other = _user(db, "x@x.com")
    _create(db, store, owner, title="mine")
    _create(db, store, other, title="theirs")
    rows, _ = service.list_page(db, principal=_principal(owner))
    assert [a.title for a in rows] == ["mine"]


def test_update_bumps_version_swaps_file_and_drops_old_object(db, store):
    user = _user(db)
    row = _create(db, store, user, content={"markdown": "v1"})
    old_file_id = row.file_id
    old_key = db.get(File, old_file_id).object_key
    updated = service.update(
        db,
        store,
        row.id,
        principal=_principal(user),
        bucket=BUCKET,
        content={"markdown": "v2"},
    )
    assert updated.version == 2
    assert updated.file_id != old_file_id
    assert db.get(File, old_file_id) is None
    new_row = db.get(File, updated.file_id)
    assert new_row is not None
    assert _keys(store) == {new_row.object_key}
    assert new_row.object_key != old_key
    _, content = service.get(db, store, row.id, principal=_principal(user))
    assert content == {"markdown": "v2"}


def test_update_other_users_artifact_raises_not_found(db, store):
    owner = _user(db, "own@x.com")
    stranger = _user(db, "str@x.com")
    row = _create(db, store, owner, content={"markdown": "v1"})
    with pytest.raises(service.NotFound):
        service.update(
            db,
            store,
            row.id,
            principal=_principal(stranger),
            bucket=BUCKET,
            content={"markdown": "v2"},
        )
    # The failed update wrote nothing.
    assert db.get(ChatArtifact, row.id).version == 1
    assert len(store.list_objects()) == 1


def test_delete_removes_row_file_and_object(db, store):
    user = _user(db)
    row = _create(db, store, user)
    file_id = row.file_id
    service.delete(db, store, row.id, principal=_principal(user))
    assert db.get(ChatArtifact, row.id) is None
    assert db.get(File, file_id) is None
    assert store.list_objects() == []


def test_delete_other_users_artifact_raises_not_found(db, store):
    owner = _user(db, "own@x.com")
    stranger = _user(db, "str@x.com")
    row = _create(db, store, owner)
    file_id = row.file_id
    with pytest.raises(service.NotFound):
        service.delete(db, store, row.id, principal=_principal(stranger))
    assert db.get(ChatArtifact, row.id) is not None
    assert db.get(File, file_id) is not None
    assert len(store.list_objects()) == 1


def test_users_remove_purges_artifacts_before_files_detach(session_factory):
    store = FakeObjectStore()
    with session_factory() as db:
        victim = users.register(db, "victim@x.com", "s3cret123")
        caller = users.register(db, "caller@x.com", "s3cret123")
        db.commit()
        personal = users.tenant_id_for_user(db, victim.id)
        row = _create(db, store, victim, title="keep me", principal=_principal(victim, personal))
        file_id = row.file_id
        users.remove(db, victim.id, caller_id=caller.id, store=store)
        db.commit()
        assert db.get(User, victim.id) is None
        assert db.get(ChatArtifact, row.id) is None
        assert db.get(File, file_id) is None
        assert store.list_objects() == []


def test_file_delete_while_artifact_refs_it_hits_restrict(session_factory):
    # A raw file-row delete while the artifact references it must fail:
    # this is the ordering RESTRICT enforces on every consumer.
    store = FakeObjectStore()
    with session_factory() as db:
        owner = _user(db, "r@x.com")
        row = _create(db, store, owner)
        db.commit()
        db.delete(db.get(File, row.file_id))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()


def test_thread_delete_nulls_thread_id_artifact_survives(db, store, session_factory):
    user = _user(db)
    with tenant_scope("t1"):
        thread = ChatThread(user_id=user.id, tenant_id="t1", title="t")
        db.add(thread)
        db.flush()
    row = _create(db, store, user, thread_id=thread.id)
    assert row.thread_id == thread.id
    db.delete(thread)
    db.commit()
    db.close()
    with session_factory() as fresh:
        art = fresh.scalar(select(ChatArtifact).where(ChatArtifact.id == row.id))
        assert art is not None
        assert art.thread_id is None
        # The file row and object survive too.
        assert fresh.get(File, art.file_id) is not None
    assert len(store.list_objects()) == 1


def test_purge_user_deletes_artifacts_and_file_rows(session_factory):
    store = FakeObjectStore()
    with session_factory() as db:
        owner = _user(db, "p@x.com")
        _create(db, store, owner, title="a")
        _create(db, store, owner, title="b")
        db.commit()
        service.purge_user(db, store, user_id=owner.id)
        db.commit()
        assert db.scalars(select(ChatArtifact)).all() == []
        assert db.scalars(select(File)).all() == []
        assert store.list_objects() == []
