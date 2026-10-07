from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from api import authz, sessions, users
from api.db import DbSession
from api.schemas import MeOut, UserCreate
from api.verifiers import CredentialVerifier, get_credential_verifier

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", status_code=204)
def login(
    payload: UserCreate,
    response: Response,
    db: DbSession,
    verifier: Annotated[CredentialVerifier, Depends(get_credential_verifier)],
) -> None:
    user = verifier.verify(db, payload.email, payload.password)
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
def me(principal: Annotated[authz.Principal, Depends(authz.current_principal)]) -> MeOut:
    return MeOut(
        id=principal.user_id,
        email=principal.email,
        tenant_id=principal.tenant_id,
        roles=list(principal.roles),
    )
