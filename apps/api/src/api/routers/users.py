from fastapi import APIRouter, HTTPException

from api.db import DbSession
from api.models import User
from api.repositories import UserRepository
from api.schemas import UserCreate, UserOut
from api.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(db: DbSession) -> list[User]:
    return UserRepository(db).list()


@router.post("", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: DbSession) -> User:
    repo = UserRepository(db)
    if repo.get_by_email(payload.email):
        raise HTTPException(status_code=409, detail="email already registered")
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    return repo.add(user)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: DbSession) -> User:
    user = UserRepository(db).get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: DbSession) -> None:
    repo = UserRepository(db)
    user = repo.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    repo.delete(user)
