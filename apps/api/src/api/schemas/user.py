from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserActivationUpdate(BaseModel):
    active: bool


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserPageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[UserOut]
    total: int
    total_all: int
    page: int
    page_size: int


class UserProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    display_name: str | None
    avatar_url: str | None
    bio: str | None
    created_at: datetime
    updated_at: datetime


class UserTenantMembershipOut(BaseModel):
    tenant_id: str
    roles: list[str]


class UserDetailOut(UserOut):
    profile: UserProfileOut | None
    system_roles: list[str]
    tenants: list[UserTenantMembershipOut]
