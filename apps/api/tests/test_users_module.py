"""Users module tests: real session, no HTTP. The router mapping is pinned in test_users.py."""

import pytest
from api import users
from api.credentials import verify_password
from api.models import SystemRole, Tenant, TenantDek, User, UserSystemRole
from api.users import listing
from crypto import tenant_scope


def test_register_hashes_password(session_factory):
    with session_factory() as db:
        user = users.register(db, "reg@x.com", "s3cret123")

        assert isinstance(user, User)
        assert user.id is not None
        assert user.hashed_password != "s3cret123"
        assert verify_password("s3cret123", user.hashed_password) is True


def test_duplicate_email_raises_email_taken(session_factory):
    with session_factory() as db:
        users.register(db, "dup@x.com", "s3cret123")

        with pytest.raises(users.EmailTaken):
            users.register(db, "dup@x.com", "s3cret123")


def test_get_returns_user(session_factory):
    with session_factory() as db:
        created = users.register(db, "get@x.com", "s3cret123")

        fetched = users.get(db, created.id)

        assert fetched.id == created.id
        assert fetched.email == "get@x.com"


def test_get_missing_raises_not_found(session_factory):
    with session_factory() as db, pytest.raises(users.NotFound):
        users.get(db, 424242)


def test_remove_deletes_user(session_factory):
    with session_factory() as db:
        user = users.register(db, "gone@x.com", "s3cret123")

        users.remove(db, user.id, caller_id=user.id + 1)

        with pytest.raises(users.NotFound):
            users.get(db, user.id)


def test_remove_missing_raises_not_found(session_factory):
    with session_factory() as db, pytest.raises(users.NotFound):
        users.remove(db, 424242, caller_id=1)


def test_remove_refuses_self(session_factory):
    with session_factory() as db:
        user = users.register(db, "selfdel@x.com", "s3cret123")
        db.commit()

        with pytest.raises(users.SelfChange):
            users.remove(db, user.id, caller_id=user.id)


def test_remove_refuses_last_active_owner(session_factory):
    with session_factory() as db:
        first = users.register(db, "del-a@x.com", "s3cret123")
        second = users.register(db, "del-b@x.com", "s3cret123")
        db.add(UserSystemRole(user_id=first.id, role=SystemRole.SYSTEM_OWNER))
        db.add(UserSystemRole(user_id=second.id, role=SystemRole.SYSTEM_OWNER))
        db.commit()

        users.set_active(db, second.id, False, caller_id=first.id)

        with pytest.raises(users.LastActiveOwner):
            users.remove(db, first.id, caller_id=second.id)


def test_list_is_instance_wide_across_personal_tenants(session_factory):
    with session_factory() as db:
        users.register(db, "wide-a@x.com", "s3cret123")
        users.register(db, "wide-b@x.com", "s3cret123")

        emails = {user.email for user in listing.list_page(db).items}

    # Each user sits in a personal tenant, yet the list shows both: the
    # instance owner administers the whole instance until invites land.
    assert {"wide-a@x.com", "wide-b@x.com"} <= emails


def test_tenant_id_for_user_without_tenant_raises_not_found(session_factory):
    with session_factory() as db:
        # A user row with no tenant link; register always attaches one.
        orphan = User(email="orphan@x.com", hashed_password="not-a-hash")
        db.add(orphan)
        db.flush()

        with pytest.raises(users.NotFound):
            users.tenant_id_for_user(db, orphan.id)


def test_listing_returns_users_by_id(session_factory):
    with session_factory() as db:
        users.register(db, "b@x.com", "s3cret123")
        users.register(db, "a@x.com", "s3cret123")

        page = listing.list_page(db)

        assert [u.email for u in page.items] == ["b@x.com", "a@x.com"]


def test_set_active_flips_flag(session_factory):
    with session_factory() as db:
        user = users.register(db, "act@x.com", "s3cret123")
        db.commit()

        updated = users.set_active(db, user.id, False, caller_id=user.id + 1)

        assert updated.is_active is False


def test_set_active_missing_raises_not_found(session_factory):
    with session_factory() as db, pytest.raises(users.NotFound):
        users.set_active(db, 424242, False, caller_id=1)


def test_set_active_self_raises(session_factory):
    with session_factory() as db:
        user = users.register(db, "selfact@x.com", "s3cret123")
        db.commit()

        with pytest.raises(users.SelfChange):
            users.set_active(db, user.id, False, caller_id=user.id)


def test_set_active_refuses_last_active_owner(session_factory):
    with session_factory() as db:
        first = users.register(db, "own-a@x.com", "s3cret123")
        second = users.register(db, "own-b@x.com", "s3cret123")
        db.add(UserSystemRole(user_id=first.id, role=SystemRole.SYSTEM_OWNER))
        db.add(UserSystemRole(user_id=second.id, role=SystemRole.SYSTEM_OWNER))
        db.commit()

        users.set_active(db, second.id, False, caller_id=first.id)

        with pytest.raises(users.LastActiveOwner):
            users.set_active(db, first.id, False, caller_id=second.id)


def test_remove_deletes_personal_tenant_and_dek(session_factory):
    with session_factory() as db:
        user = users.register(db, "dekt@x.com", "s3cret123")
        db.commit()
        tenant_id = users.tenant_id_for_user(db, user.id)
        # Tenant-carrying writes must flush inside the scope they point at.
        with tenant_scope(tenant_id):
            db.add(TenantDek(tenant_id=tenant_id, key_id="k1", wrapped_dek="w" * 40))
            db.flush()
        db.commit()

        users.remove(db, user.id, caller_id=user.id + 1)

        assert db.get(Tenant, tenant_id) is None
        assert db.get(TenantDek, tenant_id) is None
