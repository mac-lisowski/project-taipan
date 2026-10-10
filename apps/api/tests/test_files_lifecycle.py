"""File lifecycle: detach_user, detach_tenant, and the user-delete wiring.

Real session, FakeObjectStore, no HTTP except the one integration case.
The router mapping lives in test_files_http.py; the service choreography
lives in test_files_service.py.
"""

import io

import pytest
from api import users
from api.config import get_config
from api.files.lifecycle import detach_tenant, detach_user
from api.models import File, Tenant, User, UserTenant
from api_testsupport import create_user, setup_admin
from crypto import tenant_scope
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from storage import FakeObjectStore, StorageError

# Objects delete under row.bucket, so rows and the fake store share one name.
BUCKET = get_config().storage.s3_bucket


def _user(db, email="u@x.com"):
    user = User(email=email, hashed_password="x")
    db.add(user)
    db.flush()
    return user


def _file(db, *, user_id, tenant_id, scope, key):
    row = File(
        tenant_id=tenant_id,
        scope=scope,
        created_by_user_id=user_id,
        purpose="attachment",
        bucket=BUCKET,
        object_key=key,
        filename="f.bin",
        content_type="text/plain",
        size_bytes=1,
        sha256="a" * 64,
    )
    # Tenant-carrying writes must flush inside the scope they point at.
    with tenant_scope(tenant_id):
        db.add(row)
        db.flush()
    return row


def _put(store, key):
    store.put(BUCKET, key, io.BytesIO(b"x"), content_type="text/plain", size=1)


def _keys(store):
    return {obj.key for obj in store.list_objects()}


class _RaisingStore(FakeObjectStore):
    """Every object delete fails, to prove a detach swallows storage errors."""

    def delete(self, bucket: str, key: str) -> None:
        raise StorageError("store down")


def test_detach_user_purges_private_rows_and_objects(session_factory):
    store = FakeObjectStore()
    with session_factory() as db:
        user = _user(db)
        private = _file(db, user_id=user.id, tenant_id="t1", scope="user", key="private")
        shared = _file(db, user_id=user.id, tenant_id="t1", scope="tenant", key="shared")
        _put(store, "private")
        _put(store, "shared")
        db.commit()

        detach_user(db, store, user_id=user.id)
        db.commit()

        assert db.get(File, private.id) is None
        # The private object goes; the shared object stays with its row.
        assert _keys(store) == {"shared"}
        kept = db.get(File, shared.id)
        assert kept is not None
        assert kept.created_by_user_id is None


def test_detach_user_survives_a_failing_object_delete(session_factory):
    store = _RaisingStore()
    with session_factory() as db:
        user = _user(db)
        private = _file(db, user_id=user.id, tenant_id="t1", scope="user", key="private")
        db.commit()

        # The row goes even when the object store is down.
        detach_user(db, store, user_id=user.id)
        db.commit()

        assert db.get(File, private.id) is None


def test_detach_user_passes_flush_guard_under_foreign_scope(session_factory):
    store = FakeObjectStore()
    with session_factory() as db:
        user = _user(db)
        _file(db, user_id=user.id, tenant_id="t1", scope="user", key="private")
        shared = _file(db, user_id=user.id, tenant_id="t1", scope="tenant", key="shared")
        db.commit()

        # The caller sits in a foreign scope; detach_user must switch to the
        # victim's scope or the nulling flush trips the guard.
        with tenant_scope("other-tenant"):
            detach_user(db, store, user_id=user.id)
        db.commit()

        assert db.get(File, shared.id).created_by_user_id is None


def test_raw_user_delete_without_detach_hits_restrict(session_factory):
    with session_factory() as db:
        user = _user(db)
        _file(db, user_id=user.id, tenant_id="t1", scope="user", key="private")
        db.commit()

        db.delete(user)
        # RESTRICT on created_by_user_id forces the delete through detach_user.
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()


def test_detach_tenant_purges_every_row_and_object(session_factory):
    store = FakeObjectStore()
    with session_factory() as db:
        owner = _user(db, "owner@x.com")
        other = _user(db, "other@x.com")
        shared = _file(db, user_id=owner.id, tenant_id="t1", scope="tenant", key="shared")
        private = _file(db, user_id=owner.id, tenant_id="t1", scope="user", key="private")
        kept = _file(db, user_id=other.id, tenant_id="t2", scope="tenant", key="kept")
        for key in ("shared", "private", "kept"):
            _put(store, key)
        db.commit()

        detach_tenant(db, store, tenant_id="t1")
        db.commit()

        assert db.get(File, shared.id) is None
        assert db.get(File, private.id) is None
        assert db.get(File, kept.id) is not None
        assert _keys(store) == {"kept"}


def test_tenant_file_outlives_its_uploader(session_factory):
    store = FakeObjectStore()
    with session_factory() as db:
        user = _user(db)
        shared = _file(db, user_id=user.id, tenant_id="t1", scope="tenant", key="shared")
        _put(store, "shared")
        db.commit()

        detach_user(db, store, user_id=user.id)
        db.delete(user)
        db.flush()
        db.commit()

        assert db.get(User, user.id) is None
        kept = db.get(File, shared.id)
        assert kept is not None
        assert kept.created_by_user_id is None
        assert _keys(store) == {"shared"}


def test_users_remove_purges_private_keeps_surviving_tenant_file(session_factory):
    store = FakeObjectStore()
    with session_factory() as db:
        victim = users.register(db, "victim@x.com", "s3cret123")
        caller = users.register(db, "caller@x.com", "s3cret123")
        db.commit()
        personal = users.tenant_id_for_user(db, victim.id)
        surviving = users.tenant_id_for_user(db, caller.id)
        private = _file(db, user_id=victim.id, tenant_id=personal, scope="user", key="private")
        shared = _file(db, user_id=victim.id, tenant_id=surviving, scope="tenant", key="shared")
        _put(store, "private")
        _put(store, "shared")
        db.commit()

        users.remove(db, victim.id, caller_id=caller.id, store=store)
        db.commit()

        assert db.get(File, private.id) is None
        assert db.get(User, victim.id) is None
        assert db.get(Tenant, personal) is None
        # The tenant file survives its uploader because its tenant lives.
        assert _keys(store) == {"shared"}
        kept = db.get(File, shared.id)
        assert kept is not None
        assert kept.created_by_user_id is None


def test_delete_user_http_purges_files(client, session_factory):
    store = FakeObjectStore()
    # The lifespan installs a real S3 store; the route reads app.state per
    # request, so this overwrite wins.
    client.app.state.object_store = store
    setup_admin(client, "admin@x.com")
    victim = create_user(client, "victim@x.com")
    caller = create_user(client, "caller@x.com")
    with session_factory() as db:
        personal = db.scalar(select(UserTenant.tenant_id).where(UserTenant.user_id == victim))
        surviving = db.scalar(select(UserTenant.tenant_id).where(UserTenant.user_id == caller))
        private = _file(db, user_id=victim, tenant_id=personal, scope="user", key="private")
        shared = _file(db, user_id=victim, tenant_id=surviving, scope="tenant", key="shared")
        db.commit()
        private_id, shared_id = private.id, shared.id
    _put(store, "private")
    _put(store, "shared")

    resp = client.delete(f"/api/users/{victim}")

    assert resp.status_code == 204
    with session_factory() as db:
        assert db.get(File, private_id) is None
        assert db.get(User, victim) is None
        kept = db.get(File, shared_id)
        assert kept is not None
        assert kept.created_by_user_id is None
    assert _keys(store) == {"shared"}
