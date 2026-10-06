"""Authorization: role checks over the session cookie."""

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from api import sessions
from api.db import DbSession
from api.models import Role, User, UserRole

__all__ = ["current_user", "require_admin", "resolve_session", "roles_for"]


def roles_for(db: Session, user_id: int) -> list[str]:
    query = select(UserRole.role).where(UserRole.user_id == user_id).order_by(UserRole.role)
    return list(db.scalars(query).all())


def resolve_session(request: Request) -> sessions.SessionData | None:
    token = request.cookies.get(sessions.COOKIE_NAME)
    return sessions.resolve(token) if token else None


def current_user(request: Request, db: DbSession) -> User:
    sess = resolve_session(request)
    if sess is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    user = db.get(User, sess.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    return user


def require_admin(request: Request, db: DbSession) -> User:
    user = current_user(request, db)
    if Role.ADMIN not in roles_for(db, user.id):
        raise HTTPException(status_code=403, detail="admin role required")
    return user
