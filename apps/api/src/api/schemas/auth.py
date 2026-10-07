from pydantic import BaseModel, EmailStr


class MeOut(BaseModel):
    id: int
    email: EmailStr
    tenant_id: str
    roles: list[str] = []


class SetupStatus(BaseModel):
    needs_setup: bool


class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: str
    confirm_new_password: str


class PasswordChangeOut(BaseModel):
    other_devices_signed_out: bool
