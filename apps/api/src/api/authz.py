"""Authorization: role checks over the session cookie."""

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from api import sessions
from api.db import DbSession
from api.models import Role, User, UserRole

__all__ = ["require_admin", "roles_for"]


def roles_for(db: Session, user_id: int) -> list[str]:
    query = select(UserRole.role).where(UserRole.user_id == user_id).order_by(UserRole.role)
    return list(db.scalars(query).all())


def require_admin(request: Request, db: DbSession) -> User:
    token = request.cookies.get(sessions.COOKIE_NAME)
    row = sessions.resolve(db, token) if token else None
    user = db.get(User, row.user_id) if row else None
    if user is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    if Role.ADMIN not in roles_for(db, user.id):
        raise HTTPException(status_code=403, detail="admin role required")
    return user
