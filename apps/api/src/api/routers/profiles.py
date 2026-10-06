from fastapi import APIRouter, HTTPException

from api import users
from api.db import DbSession
from api.models import User, UserProfile
from api.schemas import ProfileRead, ProfileUpdate

router = APIRouter(prefix="/users", tags=["profiles"])


def _require_user(user_id: int, db: DbSession) -> User:
    try:
        return users.get(db, user_id)
    except users.NotFound:
        raise HTTPException(status_code=404, detail="user not found")


@router.get("/{user_id}/profile", response_model=ProfileRead)
def get_profile(user_id: int, db: DbSession) -> UserProfile:
    user = _require_user(user_id, db)
    profile = user.profile
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not found")
    return profile


@router.put("/{user_id}/profile", response_model=ProfileRead)
def upsert_profile(user_id: int, payload: ProfileUpdate, db: DbSession) -> UserProfile:
    user = _require_user(user_id, db)
    profile = user.profile
    if profile is None:
        profile = UserProfile(user_id=user_id, **payload.model_dump())
    else:
        for field, value in payload.model_dump().items():
            setattr(profile, field, value)
    db.add(profile)
    # The get_db teardown owns the commit; flush only gets the PK out.
    db.flush()
    db.refresh(profile)
    return profile
