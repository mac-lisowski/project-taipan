"""System settings home: global key value store and the registration switch."""

from api.system_settings.service import (
    REGISTRATION_ENABLED,
    get,
    get_registration_enabled,
    set,
    set_registration_enabled,
)

__all__ = [
    "REGISTRATION_ENABLED",
    "get",
    "get_registration_enabled",
    "set",
    "set_registration_enabled",
]
