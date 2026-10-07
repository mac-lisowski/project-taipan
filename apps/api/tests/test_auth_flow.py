"""Auth flow module tests: credential to token at the module seam. No HTTP, no cookies."""

import inspect
from types import SimpleNamespace

import pytest
from api import auth_flow, sessions, users
from api.models import User, UserTenant
from sqlalchemy import select
from sqlalchemy.orm import Session

EMAIL = "flow@x.com"
PASSWORD = "s3cret123"


class FakeVerifier:
    """Injected verifier: accepts any password for one known email."""

    def __init__(self, user_id: int, email: str) -> None:
        self.user_id = user_id
        self.email = email
        self.calls: list[tuple[str, str]] = []

    def verify(self, db: Session, email: str, password: str):
        # Body fields must reach the verifier untouched; that is the mapping.
        self.calls.append((email, password))
        if email == self.email:
            return SimpleNamespace(id=self.user_id)
        return None


class RejectingVerifier:
    """Injected verifier: no credential ever verifies."""

    def verify(self, db: Session, email: str, password: str):
        return None


def _tenant_id_of(db: Session, user_id: int) -> str:
    """Expected tenant from the UserTenant table, not via the users helper."""
    return db.scalar(select(UserTenant.tenant_id).where(UserTenant.user_id == user_id))


def test_login_success_returns_token_for_right_user_and_tenant(
    session_factory, memory_session_store
):
    with session_factory() as db:
        user = users.register(db, EMAIL, PASSWORD)
        verifier = FakeVerifier(user.id, EMAIL)

        token = auth_flow.login(db, verifier, EMAIL, PASSWORD)

        data = sessions.resolve(token)
        assert data is not None
        assert data.user_id == user.id
        assert data.tenant_id == _tenant_id_of(db, user.id)
        # One session landed in the store for this login.
        assert len(memory_session_store.entries) == 1


def test_login_verifier_none_raises_invalid_credentials_without_mint(
    session_factory, memory_session_store
):
    with session_factory() as db, pytest.raises(auth_flow.InvalidCredentials):
        auth_flow.login(db, RejectingVerifier(), EMAIL, PASSWORD)

    assert memory_session_store.entries == {}


def test_verifier_receives_email_and_password_untouched(session_factory):
    with session_factory() as db:
        user = users.register(db, EMAIL, PASSWORD)
        verifier = FakeVerifier(user.id, EMAIL)

        auth_flow.login(db, verifier, EMAIL, PASSWORD)

        assert verifier.calls == [(EMAIL, PASSWORD)]


def test_issue_mints_session_with_users_own_tenant(session_factory, memory_session_store):
    with session_factory() as db:
        user = users.register(db, EMAIL, PASSWORD)
        expected_tenant = _tenant_id_of(db, user.id)

        token = auth_flow.issue(db, user.id)

        data = sessions.resolve(token)
        assert data is not None
        assert data.user_id == user.id
        assert data.tenant_id == expected_tenant


def test_issue_orphan_user_propagates_not_found_without_mint(session_factory, memory_session_store):
    with session_factory() as db:
        # A user row with no tenant link; register always attaches one.
        orphan = User(email="orphan@x.com", hashed_password="not-a-hash")
        db.add(orphan)
        db.flush()

        with pytest.raises(users.NotFound):
            auth_flow.issue(db, orphan.id)

    assert memory_session_store.entries == {}


def _module_functions():
    for obj in vars(auth_flow).values():
        if inspect.isfunction(obj) and obj.__module__ == auth_flow.__name__:
            yield obj


def test_module_surface_takes_no_response_or_cookie_parameter():
    functions = {fn.__name__: fn for fn in _module_functions()}
    # The scan must not be vacuous: the module's real surface is present.
    assert {"issue", "login"} <= functions.keys()
    flagged = [
        f"{fn.__name__}.{param.name}"
        for fn in functions.values()
        for param in inspect.signature(fn).parameters.values()
        if "response" in param.name.lower() or "cookie" in param.name.lower()
    ]
    assert flagged == []


def test_module_exports_no_revoke_all():
    assert not hasattr(auth_flow, "revoke_all")
    assert "revoke_all" not in getattr(auth_flow, "__all__", [])
