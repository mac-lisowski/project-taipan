from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# These caps mirror the CHECK constraints on user_profiles, so oversize
# input fails at the edge with 422 instead of at insert with 500.
DISPLAY_NAME_MAX = 100
AVATAR_URL_MAX = 2048
BIO_MAX = 5000


class ProfileCreate(BaseModel):
    display_name: str | None = Field(default=None, max_length=DISPLAY_NAME_MAX)
    avatar_url: str | None = Field(default=None, max_length=AVATAR_URL_MAX)
    bio: str | None = Field(default=None, max_length=BIO_MAX)


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
