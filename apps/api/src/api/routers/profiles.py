from fastapi import APIRouter, HTTPException

from api import profiles, users
from api.db import DbSession
from api.models import UserProfile
from api.schemas import ProfileRead, ProfileUpdate

router = APIRouter(prefix="/users", tags=["profiles"])


@router.get("/{user_id}/profile", response_model=ProfileRead)
def get_profile(user_id: int, db: DbSession) -> UserProfile:
    try:
        return profiles.get(db, user_id)
    except users.NotFound:
        raise HTTPException(status_code=404, detail="user not found")
    except profiles.NotFound:
        raise HTTPException(status_code=404, detail="profile not found")


@router.put("/{user_id}/profile", response_model=ProfileRead)
def upsert_profile(user_id: int, payload: ProfileUpdate, db: DbSession) -> UserProfile:
    try:
        return profiles.upsert(
            db,
            user_id,
            display_name=payload.display_name,
            avatar_url=payload.avatar_url,
            bio=payload.bio,
        )
    except users.NotFound:
        raise HTTPException(status_code=404, detail="user not found")
