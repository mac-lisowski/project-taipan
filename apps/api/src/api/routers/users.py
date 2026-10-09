from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from api import users
from api.authz import Principal, require_system_owner
from api.db import DbSession
from api.models import User
from api.schemas import UserActivationUpdate, UserCreate, UserDetailOut, UserOut, UserPageOut
from api.users import listing

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_system_owner)])


@router.get("", response_model=UserPageOut)
def list_users(
    db: DbSession,
    q: Annotated[str, Query(max_length=200)] = "",
    status: Annotated[Literal["all", "active", "inactive"], Query()] = "all",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query()] = listing.DEFAULT_PAGE_SIZE,
) -> listing.UsersPage:
    # Query params arrive as strings, so int literals cannot validate them.
    if page_size not in listing.PAGE_SIZES:
        raise HTTPException(status_code=422, detail="page_size must be 10, 25, or 50")
    return listing.list_page(db, q=q, status=status, page=page, page_size=page_size)


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
