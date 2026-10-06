from fastapi import APIRouter, HTTPException, Response

from api import sessions, users
from api.db import DbSession
from api.models import User
from api.schemas import UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_COOKIE = "session"


def _set_session_cookie(response: Response, token: str) -> None:
    # Secure stays out until the app serves https only.
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", path="/")


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserCreate, response: Response, db: DbSession) -> User:
    try:
        user = users.register(db, payload.email, payload.password)
    except users.EmailTaken as exc:
        raise HTTPException(status_code=409, detail="email already registered") from exc
    _set_session_cookie(response, sessions.mint(db, user.id))
    return user
