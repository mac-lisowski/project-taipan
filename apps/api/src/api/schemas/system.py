from pydantic import BaseModel


class RegistrationSwitchOut(BaseModel):
    enabled: bool


class RegistrationSwitchIn(BaseModel):
    enabled: bool
