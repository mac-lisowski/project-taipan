"""Authorization: role checks over the session cookie."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select

from api import sessions
from api.db import DbSession
from api.models import Role, SystemRole, User, UserSystemRole, UserTenantRole

__all__ = [
    "Principal",
    "can",
    "current_principal",
    "require_admin",
    "require_system_owner",
    "resolve_session",
]


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: int
    email: str
    tenant_id: str
    roles: tuple[str, ...]
    system_roles: tuple[str, ...] = ()

    def has_role(self, role: str) -> bool:
        return role in self.roles


def resolve_session(request: Request) -> sessions.SessionData | None:
    token = request.cookies.get(sessions.COOKIE_NAME)
    if not token:
        return None
    found, data = sessions.cached_session(request, token)
    if found:
        return data
    data = sessions.resolve(token)
    sessions.remember_resolved_session(request, token, data)
    return data


def current_principal(request: Request, db: DbSession) -> Principal:
    sess = resolve_session(request)
    if sess is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    row = db.execute(
        select(User.id, User.email, User.is_active).where(User.id == sess.user_id)
    ).first()
    # A missing or deactivated user must not ride a live session.
    if row is None or not row.is_active:
        raise HTTPException(status_code=401, detail="not authenticated")
    # Roles bound to another tenant must not ride along, or admin leaks across tenants.
    roles = tuple(
        db.scalars(
            select(UserTenantRole.role)
            .where(
                UserTenantRole.user_id == sess.user_id,
                UserTenantRole.tenant_id == sess.tenant_id,
            )
            .order_by(UserTenantRole.role)
        ).all()
    )
    system_roles = tuple(
        db.scalars(
            select(UserSystemRole.role)
            .where(UserSystemRole.user_id == sess.user_id)
            .order_by(UserSystemRole.role)
        ).all()
    )
    return Principal(
        user_id=row[0],
        email=row[1],
        tenant_id=sess.tenant_id,
        roles=roles,
        system_roles=system_roles,
    )


def require_admin(
    principal: Annotated[Principal, Depends(current_principal)],
) -> Principal:
    # roles is already filtered to the session tenant, so admin here is that tenant's admin.
    if not principal.has_role(Role.ADMIN):
        raise HTTPException(status_code=403, detail="admin role required")
    return principal


def require_system_owner(
    principal: Annotated[Principal, Depends(current_principal)],
) -> Principal:
    if SystemRole.SYSTEM_OWNER.value not in principal.system_roles:
        raise HTTPException(status_code=403, detail="system owner role required")
    return principal


def can(db: DbSession, user_id: int, role: str, tenant_id: str | None) -> bool:
    """The one role question: user holds role in tenant; a None tenant asks the system tier."""
    if tenant_id is None:
        found = db.scalar(
            select(UserSystemRole.user_id)
            .where(
                UserSystemRole.user_id == user_id,
                UserSystemRole.role == role,
            )
            .limit(1)
        )
        return found is not None
    found = db.scalar(
        select(UserTenantRole.user_id)
        .where(
            UserTenantRole.user_id == user_id,
            UserTenantRole.tenant_id == tenant_id,
            UserTenantRole.role == role,
        )
        .limit(1)
    )
    return found is not None
