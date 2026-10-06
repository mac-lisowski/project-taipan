from fastapi import APIRouter, HTTPException, Response

from api import sessions, users
from api.db import DbSession
from api.models import User
from api.schemas import SetupStatus, UserCreate, UserOut

router = APIRouter(prefix="/setup", tags=["setup"])


@router.get("", response_model=SetupStatus)
def probe(db: DbSession) -> SetupStatus:
    return SetupStatus(needs_setup=users.needs_setup(db))


@router.post("", response_model=UserOut, status_code=201)
def setup(payload: UserCreate, response: Response, db: DbSession) -> User:
    try:
        user = users.bootstrap(db, payload.email, payload.password)
    except users.AlreadySetup as exc:
        raise HTTPException(status_code=409, detail="setup already completed") from exc
    # Secure stays out until the app serves https only.
    response.set_cookie(
        sessions.COOKIE_NAME, sessions.mint(db, user.id), httponly=True, samesite="lax", path="/"
    )
    return user
