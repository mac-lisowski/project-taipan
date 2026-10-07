"""Authorization: role checks over the session cookie."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from api import sessions
from api.db import DbSession
from api.models import Role, User, UserRole

__all__ = [
    "Principal",
    "current_principal",
    "require_admin",
    "resolve_session",
    "roles_for",
]


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: int
    email: str
    tenant_id: str
    roles: tuple[str, ...]

    def has_role(self, role: str) -> bool:
        return role in self.roles


def roles_for(db: Session, user_id: int) -> list[str]:
    query = select(UserRole.role).where(UserRole.user_id == user_id).order_by(UserRole.role)
    return list(db.scalars(query).all())


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
    query = (
        select(User.id, User.email, UserRole.role)
        .outerjoin(UserRole, UserRole.user_id == User.id)
        .where(User.id == sess.user_id)
        .order_by(UserRole.role)
    )
    rows = db.execute(query).all()
    if not rows:
        raise HTTPException(status_code=401, detail="not authenticated")
    roles = tuple(r[2] for r in rows if r[2] is not None)
    return Principal(
        user_id=rows[0][0],
        email=rows[0][1],
        tenant_id=sess.tenant_id,
        roles=roles,
    )


def require_admin(
    principal: Annotated[Principal, Depends(current_principal)],
) -> Principal:
    if not principal.has_role(Role.ADMIN):
        raise HTTPException(status_code=403, detail="admin role required")
    return principal
