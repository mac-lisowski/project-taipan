"""Registration home: the switch-gated request act and the activate act."""

from api.registration.service import RegistrationClosed, WeakPassword, activate, request

__all__ = [
    "RegistrationClosed",
    "WeakPassword",
    "activate",
    "request",
]
