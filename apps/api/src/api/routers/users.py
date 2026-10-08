from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from api import users
from api.authz import Principal, require_system_owner
from api.db import DbSession
from api.models import User
from api.schemas import UserActivationUpdate, UserCreate, UserDetailOut, UserOut

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_system_owner)])


@router.get("", response_model=list[UserOut])
def list_users(db: DbSession) -> list[User]:
    return users.list(db)


@router.post("", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: DbSession) -> User:
    try:
        return users.register(db, payload.email, payload.password)
    except users.EmailTaken as exc:
        raise HTTPException(status_code=409, detail="email already registered") from exc
    except users.WeakPassword as exc:
        raise HTTPException(
            status_code=422, detail="password does not meet the strength rule"
        ) from exc


@router.get("/{user_id}", response_model=UserDetailOut)
def get_user(user_id: int, db: DbSession) -> dict:
    try:
        return users.detail(db, user_id)
    except users.NotFound as exc:
        raise HTTPException(status_code=404, detail="user not found") from exc


@router.put("/{user_id}/activation", response_model=UserOut)
def set_user_activation(
    user_id: int,
    payload: UserActivationUpdate,
    db: DbSession,
    principal: Annotated[Principal, Depends(require_system_owner)],
) -> User:
    try:
        return users.set_active(db, user_id, payload.active, principal.user_id)
    except users.NotFound as exc:
        raise HTTPException(status_code=404, detail="user not found") from exc
    except users.SelfChange as exc:
        raise HTTPException(status_code=409, detail="cannot change your own account") from exc
    except users.LastActiveOwner as exc:
        raise HTTPException(status_code=409, detail="cannot remove the last active owner") from exc


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: DbSession,
    principal: Annotated[Principal, Depends(require_system_owner)],
) -> None:
    try:
        users.remove(db, user_id, principal.user_id)
    except users.NotFound as exc:
        raise HTTPException(status_code=404, detail="user not found") from exc
    except users.SelfChange as exc:
        raise HTTPException(status_code=409, detail="cannot change your own account") from exc
    except users.LastActiveOwner as exc:
        raise HTTPException(status_code=409, detail="cannot remove the last active owner") from exc
