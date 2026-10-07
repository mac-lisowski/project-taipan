"""Users home: identity rules plus nested profiles. Usable without FastAPI."""

from api.users import profiles
from api.users.service import (
    SETUP_LOCK_KEY,
    AlreadySetup,
    EmailTaken,
    NotFound,
    WeakPassword,
    authenticate,
    bootstrap,
    get,
    list,
    needs_setup,
    register,
    remove,
    tenant_id_for_user,
)

__all__ = [
    "SETUP_LOCK_KEY",
    "AlreadySetup",
    "EmailTaken",
    "NotFound",
    "WeakPassword",
    "authenticate",
    "bootstrap",
    "get",
    "list",
    "needs_setup",
    "profiles",
    "register",
    "remove",
    "tenant_id_for_user",
]
