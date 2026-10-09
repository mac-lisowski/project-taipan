"""User identity rules: registration, lookup, removal. Usable without FastAPI."""

from __future__ import annotations

from uuid import uuid4

from crypto import tenant_scope
from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from api import sessions
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
    TenantDek,
    User,
    UserProfile,
    UserSystemRole,
    UserTenant,
    UserTenantRole,
)

__all__ = [
    "SETUP_LOCK_KEY",
    "AlreadySetup",
    "EmailTaken",
    "LastActiveOwner",
    "NotFound",
    "SelfChange",
    "WeakPassword",
    "authenticate",
    "bootstrap",
    "detail",
    "get",
    "get_by_email",
    "needs_setup",
    "register",
    "register_passwordless",
    "remove",
    "set_active",
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


class SelfChange(Exception):
    """The caller targeted their own account for deactivation or removal."""


class LastActiveOwner(Exception):
    """The change would leave the platform without an active owner."""


def register(session: Session, email: str, password: str) -> User:
    _ensure_email_free(session, email)
    ensure_acceptable(password)
    return _admit_with_personal_tenant(session, email, hash_password(password))


def register_passwordless(session: Session, email: str) -> User:
    """Create the half account: no hash yet, so no login can succeed."""
    _ensure_email_free(session, email)
    return _admit_with_personal_tenant(session, email, None)


def _ensure_email_free(session: Session, email: str) -> None:
    # One home for the taken rule so register paths cannot drift apart.
    if session.scalar(select(User).where(User.email == email)) is not None:
        raise EmailTaken(email)


def _admit_with_personal_tenant(session: Session, email: str, hashed: str | None) -> User:
    tenant = Tenant(id=uuid4().hex)
    # Tenant-carrying writes must run inside the scope they point at.
    with tenant_scope(tenant.id):
        session.add(tenant)
        user = User(email=email, hashed_password=hashed)
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
    if user.hashed_password is None:
        # A half account must fail like a wrong password, never hash None.
        return None
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


def remove(session: Session, user_id: int, caller_id: int) -> None:
    user = get(session, user_id)
    if user_id == caller_id:
        raise SelfChange(user_id)
    _ensure_not_last_active_owner(session, user)
    sessions.revoke_all(user_id)
    # The personal tenant and its data key belong to the account; both go
    # when one exists.
    tenant_id = session.scalar(select(UserTenant.tenant_id).where(UserTenant.user_id == user_id))
    session.delete(user)
    if tenant_id is not None:
        session.execute(sa_delete(TenantDek).where(TenantDek.tenant_id == tenant_id))
        session.execute(sa_delete(Tenant).where(Tenant.id == tenant_id))
    session.flush()


def set_active(session: Session, user_id: int, active: bool, caller_id: int) -> User:
    """Flip the account switch; deactivation revokes the user's sessions first."""
    user = get(session, user_id)
    if user_id == caller_id:
        raise SelfChange(user_id)
    if not active:
        _ensure_not_last_active_owner(session, user)
        sessions.revoke_all(user_id)
    user.is_active = active
    session.flush()
    session.refresh(user)
    return user


def _ensure_not_last_active_owner(session: Session, user: User) -> None:
    # Under the setup lock: racing changes must not pass the count with a stale number.
    session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": SETUP_LOCK_KEY})
    target_is_active_owner = user.is_active and (
        session.scalar(
            select(UserSystemRole.user_id).where(
                UserSystemRole.user_id == user.id,
                UserSystemRole.role == SystemRole.SYSTEM_OWNER,
            )
        )
        is not None
    )
    if not target_is_active_owner:
        return
    active_owners = session.scalar(
        select(func.count())
        .select_from(UserSystemRole)
        .join(User, User.id == UserSystemRole.user_id)
        .where(UserSystemRole.role == SystemRole.SYSTEM_OWNER, User.is_active.is_(True))
    )
    if active_owners == 1:
        raise LastActiveOwner(user.id)


def detail(session: Session, user_id: int) -> dict:
    """The account with profile, system roles, and tenant memberships joined."""
    user = get(session, user_id)
    profile = session.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    system_roles = session.scalars(
        select(UserSystemRole.role)
        .where(UserSystemRole.user_id == user_id)
        .order_by(UserSystemRole.role)
    ).all()
    rows = session.execute(
        select(UserTenant.tenant_id, UserTenantRole.role)
        .join(
            UserTenantRole,
            (UserTenantRole.user_id == UserTenant.user_id)
            & (UserTenantRole.tenant_id == UserTenant.tenant_id),
        )
        .where(UserTenant.user_id == user_id)
        .order_by(UserTenant.tenant_id, UserTenantRole.role)
    ).all()
    memberships: dict[str, list[str]] = {}
    for tenant_id, role in rows:
        memberships.setdefault(tenant_id, []).append(role)
    return {
        "id": user.id,
        "email": user.email,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "profile": profile,
        # `list` is this module's function; unpack instead of calling the builtin.
        "system_roles": [*system_roles],
        "tenants": [
            {"tenant_id": tenant_id, "roles": roles} for tenant_id, roles in memberships.items()
        ],
    }


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
