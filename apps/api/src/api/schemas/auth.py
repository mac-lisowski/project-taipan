from pydantic import BaseModel, EmailStr


class MeOut(BaseModel):
    id: int
    email: EmailStr
    tenant_id: str
    roles: list[str] = []
    system_roles: list[str] = []


class SetupStatus(BaseModel):
    needs_setup: bool


class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: str
    confirm_new_password: str


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    new_password: str


class RegisterIn(BaseModel):
    email: EmailStr


class ActivateIn(BaseModel):
    token: str
    password: str


class PasswordChangeOut(BaseModel):
    other_devices_signed_out: bool
