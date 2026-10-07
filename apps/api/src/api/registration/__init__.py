"""Registration home: the switch-gated request act and the activate act."""

from api.registration.service import APP_NAME, RegistrationClosed, WeakPassword, activate, request

__all__ = [
    "APP_NAME",
    "RegistrationClosed",
    "WeakPassword",
    "activate",
    "request",
]
