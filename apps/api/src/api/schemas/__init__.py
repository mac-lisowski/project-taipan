from api.schemas.auth import (
    ActivateIn,
    ForgotIn,
    MeOut,
    PasswordChangeIn,
    PasswordChangeOut,
    RegisterIn,
    ResetIn,
    SetupStatus,
)
from api.schemas.profile import ProfileCreate, ProfileRead, ProfileUpdate
from api.schemas.system import RegistrationSwitchIn, RegistrationSwitchOut
from api.schemas.user import UserCreate, UserOut

__all__ = [
    "ActivateIn",
    "ForgotIn",
    "MeOut",
    "PasswordChangeIn",
    "PasswordChangeOut",
    "ProfileCreate",
    "ProfileRead",
    "ProfileUpdate",
    "RegisterIn",
    "RegistrationSwitchIn",
    "RegistrationSwitchOut",
    "ResetIn",
    "SetupStatus",
    "UserCreate",
    "UserOut",
]
