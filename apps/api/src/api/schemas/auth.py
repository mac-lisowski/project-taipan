from pydantic import BaseModel, EmailStr


class MeOut(BaseModel):
    id: int
    email: EmailStr
    tenant_id: str
    roles: list[str] = []


class SetupStatus(BaseModel):
    needs_setup: bool
