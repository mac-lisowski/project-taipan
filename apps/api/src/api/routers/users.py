from fastapi import APIRouter, HTTPException

from api import users
from api.db import DbSession
from api.models import User
from api.schemas import UserCreate, UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(db: DbSession) -> list[User]:
    return users.list(db)


@router.post("", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: DbSession) -> User:
    try:
        return users.register(db, payload.email, payload.password)
    except users.EmailTaken as exc:
        raise HTTPException(status_code=409, detail="email already registered") from exc


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: DbSession) -> User:
    try:
        return users.get(db, user_id)
    except users.NotFound as exc:
        raise HTTPException(status_code=404, detail="user not found") from exc


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: DbSession) -> None:
    try:
        users.remove(db, user_id)
    except users.NotFound as exc:
        raise HTTPException(status_code=404, detail="user not found") from exc
