from api.routers.auth import router as auth_router
from api.routers.email_webhooks import router as email_webhooks_router
from api.routers.password_change import router as password_change_router
from api.routers.password_reset import router as password_reset_router
from api.routers.profiles import router as profiles_router
from api.routers.setup import router as setup_router
from api.routers.users import router as users_router

__all__ = [
    "auth_router",
    "email_webhooks_router",
    "password_change_router",
    "password_reset_router",
    "profiles_router",
    "setup_router",
    "users_router",
]
