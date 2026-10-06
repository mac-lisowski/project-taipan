from fastapi import APIRouter, HTTPException, Request, Response

from api import authz, sessions, users
from api.db import DbSession
from api.schemas import MeOut, UserCreate

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", status_code=204)
def login(payload: UserCreate, response: Response, db: DbSession) -> None:
    user = users.authenticate(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid email or password")
    tenant_id = users.tenant_id_for_user(db, user.id)
    sessions.set_session_cookie(response, sessions.mint(user.id, tenant_id))


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response) -> None:
    token = request.cookies.get(sessions.COOKIE_NAME)
    if token is not None:
        sessions.revoke(token)
    sessions.clear_session_cookie(response)


@router.get("/me", response_model=MeOut)
def me(request: Request, db: DbSession) -> MeOut:
    sess = authz.resolve_session(request)
    if sess is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    user = authz.current_user(request, db)
    return MeOut(
        id=user.id, email=user.email, tenant_id=sess.tenant_id, roles=authz.roles_for(db, user.id)
    )
