"""User identity rules: registration, lookup, removal. Usable without FastAPI."""

from __future__ import annotations

from uuid import uuid4

from crypto import tenant_scope
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from api.credentials import (
    WeakPassword,
    ensure_acceptable,
    ensure_active,
    hash_password,
    verify_password,
)
from api.models import (
    Role,
    SystemRole,
    Tenant,
    User,
    UserSystemRole,
    UserTenant,
    UserTenantRole,
)

__all__ = [
    "SETUP_LOCK_KEY",
    "AlreadySetup",
    "EmailTaken",
    "NotFound",
    "WeakPassword",
    "authenticate",
    "bootstrap",
    "get",
    "get_by_email",
    "list",
    "needs_setup",
    "register",
    "remove",
    "tenant_id_for_user",
]

# Stable advisory-lock key for first-run setup; any fixed 64-bit int works.
SETUP_LOCK_KEY = 829101


class AlreadySetup(Exception):
    """Setup ran before; the users table is not empty."""


class EmailTaken(Exception):
    """Registration hit an email that already exists."""


class NotFound(Exception):
    """No user with the requested id."""


def register(session: Session, email: str, password: str) -> User:
    if session.scalar(select(User).where(User.email == email)) is not None:
        raise EmailTaken(email)
    ensure_acceptable(password)
    tenant = Tenant(id=uuid4().hex)
    # Tenant-carrying writes must run inside the scope they point at.
    with tenant_scope(tenant.id):
        session.add(tenant)
        user = User(email=email, hashed_password=hash_password(password))
        session.add(user)
        session.flush()
        session.add(UserTenant(user_id=user.id, tenant_id=tenant.id))
        session.add(UserTenantRole(user_id=user.id, tenant_id=tenant.id, role=Role.MEMBER))
        session.flush()
        session.refresh(user)
    return user


def authenticate(session: Session, email: str, password: str) -> User | None:
    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        return None
    # Gate before verify: an inactive user never reaches hash checking.
    ensure_active(user.is_active)
    if not verify_password(password, user.hashed_password):
        return None
    return user


def get(session: Session, user_id: int) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise NotFound(user_id)
    return user


def get_by_email(session: Session, email: str) -> User | None:
    """Return the user for email, or None; the forgot flow needs no raise."""
    return session.scalar(select(User).where(User.email == email))


def list(session: Session) -> list[User]:
    # `.all()`, not `list(...)`: the name `list` is this module's function.
    # Instance-wide on purpose: one owner today; scoping arrives with invites.
    return session.scalars(select(User).order_by(User.id)).all()


def remove(session: Session, user_id: int) -> None:
    session.delete(get(session, user_id))
    session.flush()


def needs_setup(session: Session) -> bool:
    return session.scalar(select(func.count()).select_from(User)) == 0


def bootstrap(session: Session, email: str, password: str) -> User:
    """First-run setup; a concurrent second caller gets AlreadySetup. Lost role rows need a manual insert."""
    session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": SETUP_LOCK_KEY})
    if not needs_setup(session):
        raise AlreadySetup()
    user = register(session, email, password)
    tenant_id = tenant_id_for_user(session, user.id)
    # Teardown commits unscoped, so tenant-role rows must flush in here.
    with tenant_scope(tenant_id):
        session.add(UserTenantRole(user_id=user.id, tenant_id=tenant_id, role=Role.ADMIN))
        session.add(UserSystemRole(user_id=user.id, role=SystemRole.SYSTEM_OWNER))
        session.flush()
    return user


def tenant_id_for_user(session: Session, user_id: int) -> str:
    """Return the personal tenant id for user_id; raises NotFound if user has none."""
    tenant_id = session.scalar(select(UserTenant.tenant_id).where(UserTenant.user_id == user_id))
    if tenant_id is None:
        raise NotFound(user_id)
    return tenant_id
