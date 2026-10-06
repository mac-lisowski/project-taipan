from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy.orm import Session

from api import sessions, users
from api.db import DbSession
from api.models import AuthSession, User
from api.schemas import MeOut, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_COOKIE = "session"


def _set_session_cookie(response: Response, token: str) -> None:
    # Secure stays out until the app serves https only.
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", path="/")


def _resolve_session(request: Request, db: Session) -> AuthSession | None:
    token = request.cookies.get(SESSION_COOKIE)
    return sessions.resolve(db, token) if token else None


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserCreate, response: Response, db: DbSession) -> User:
    try:
        user = users.register(db, payload.email, payload.password)
    except users.EmailTaken as exc:
        raise HTTPException(status_code=409, detail="email already registered") from exc
    _set_session_cookie(response, sessions.mint(db, user.id))
    return user


@router.post("/login", status_code=204)
def login(payload: UserCreate, response: Response, db: DbSession) -> None:
    user = users.authenticate(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid email or password")
    _set_session_cookie(response, sessions.mint(db, user.id))


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: DbSession) -> None:
    row = _resolve_session(request, db)
    if row is not None:
        sessions.revoke(db, row)
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=MeOut)
def me(request: Request, db: DbSession) -> MeOut:
    row = _resolve_session(request, db)
    user = users.with_tenant(db, row.user_id) if row else None
    if user is None or user.tenant_link is None:
        # A missing session or link row scopes nothing.
        raise HTTPException(status_code=401, detail="not authenticated")
    return MeOut(id=user.id, email=user.email, tenant_id=user.tenant_link.tenant_id)
