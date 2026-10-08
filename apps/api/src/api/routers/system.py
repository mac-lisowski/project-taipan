"""Thin system routes: public switch read, owner-guarded write. No settings rules here."""

from typing import Annotated

from fastapi import APIRouter, Depends

from api import system_settings
from api.authz import Principal, require_system_owner
from api.db import DbSession
from api.schemas import RegistrationSwitchIn, RegistrationSwitchOut

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/registration", response_model=RegistrationSwitchOut)
def read_registration_switch(db: DbSession) -> RegistrationSwitchOut:
    return RegistrationSwitchOut(enabled=system_settings.get_registration_enabled(db))


@router.put("/registration", status_code=204)
def update_registration_switch(
    payload: RegistrationSwitchIn,
    db: DbSession,
    principal: Annotated[Principal, Depends(require_system_owner)],
) -> None:
    system_settings.set_registration_enabled(db, payload.enabled)
