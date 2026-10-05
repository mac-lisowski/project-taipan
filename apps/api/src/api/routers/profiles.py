from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from api.db import DbSession
from api.models import UserProfile
from api.repositories import UserRepository
from api.schemas import ProfileRead, ProfileUpdate

router = APIRouter(prefix="/users", tags=["profiles"])


def _get_user_or_404(user_id: int, db: DbSession):
    user = UserRepository(db).get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return user


@router.get("/{user_id}/profile", response_model=ProfileRead)
def get_profile(user_id: int, db: DbSession) -> UserProfile:
    _get_user_or_404(user_id, db)
    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not found")
    return profile


@router.put("/{user_id}/profile", response_model=ProfileRead)
def upsert_profile(user_id: int, payload: ProfileUpdate, db: DbSession) -> UserProfile:
    _get_user_or_404(user_id, db)
    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    if profile is None:
        profile = UserProfile(user_id=user_id, **payload.model_dump())
    else:
        for field, value in payload.model_dump().items():
            setattr(profile, field, value)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile
