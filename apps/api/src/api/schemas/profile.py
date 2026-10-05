from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProfileCreate(BaseModel):
    display_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None


class ProfileUpdate(ProfileCreate):
    # PUT is replace, so a partial body resets omitted fields to null.
    pass


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    display_name: str | None
    avatar_url: str | None
    bio: str | None
    created_at: datetime
    updated_at: datetime
