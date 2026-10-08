"""Thin profile routes: session, self service only. No token rules here."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from api import users
from api.authz import Principal, current_principal
from api.db import DbSession
from api.models import UserProfile
from api.schemas import ProfileRead, ProfileUpdate

router = APIRouter(prefix="/users", tags=["profiles"])


@router.get("/{user_id}/profile", response_model=ProfileRead)
def get_profile(
    user_id: int,
    db: DbSession,
    principal: Annotated[Principal, Depends(current_principal)],
) -> UserProfile:
    _ensure_self(user_id, principal)
    try:
        return users.profiles.get(db, user_id)
    except users.NotFound:
        raise HTTPException(status_code=404, detail="user not found")
    except users.profiles.NotFound:
        raise HTTPException(status_code=404, detail="profile not found")


@router.put("/{user_id}/profile", response_model=ProfileRead)
def upsert_profile(
    user_id: int,
    payload: ProfileUpdate,
    db: DbSession,
    principal: Annotated[Principal, Depends(current_principal)],
) -> UserProfile:
    _ensure_self(user_id, principal)
    try:
        return users.profiles.upsert(
            db,
            user_id,
            display_name=payload.display_name,
            avatar_url=payload.avatar_url,
            bio=payload.bio,
        )
    except users.NotFound:
        raise HTTPException(status_code=404, detail="user not found")


def _ensure_self(user_id: int, principal: Principal) -> None:
    # Profiles are self service; the owner reads others through the detail response.
    if user_id != principal.user_id:
        raise HTTPException(status_code=403, detail="profiles are self service")
