import os
from contextlib import asynccontextmanager

from core import greet
from fastapi import FastAPI

from api.config import get_config
from api.db import Base, SessionLocal
from api.field_crypto import build_and_register_field_crypto
from api.mail import build_email_sender
from api.middleware import TenantScopeMiddleware
from api.models.encrypted_string import EncryptedString, get_field_crypto, set_field_crypto
from api.routers import (
    auth_router,
    chat_router,
    email_webhooks_router,
    password_change_router,
    password_reset_router,
    profiles_router,
    public_router,
    registration_router,
    setup_router,
    system_router,
    threads_router,
    users_router,
)


def _encrypted_columns_exist() -> bool:
    return any(
        isinstance(col.type, EncryptedString)
        for table in Base.metadata.tables.values()
        for col in table.c
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.environ.get("API_AUTO_MIGRATE", "").lower() in ("1", "true", "yes"):
        from api import db_cli

        db_cli.upgrade()
    # Registers the crypto module when Infisical config exists; off otherwise.
    build_and_register_field_crypto()
    # Picks the mail adapter once from server config. Routes use it
    # through get_email_sender and never see the key.
    app.state.email_sender = build_email_sender(get_config(), session_factory=SessionLocal)
    if _encrypted_columns_exist() and get_field_crypto() is None:
        raise RuntimeError("EncryptedString columns exist but no crypto module is registered")
    yield
    # A repeated lifespan in one process must not serve a stale module.
    set_field_crypto(None)


app = FastAPI(lifespan=lifespan)
app.add_middleware(TenantScopeMiddleware)
app.include_router(users_router, prefix="/api")
app.include_router(profiles_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(setup_router, prefix="/api")
app.include_router(system_router, prefix="/api")
app.include_router(password_change_router, prefix="/api")
app.include_router(password_reset_router, prefix="/api")
app.include_router(registration_router, prefix="/api")
app.include_router(threads_router, prefix="/api")
app.include_router(public_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(email_webhooks_router, prefix="/api")


@app.get("/")
def root() -> dict[str, str]:
    return {"message": greet("world")}


def _serve(*, reload: bool) -> None:
    import uvicorn

    cfg = get_config()
    uvicorn.run("api.main:app", host=cfg.server.host, port=cfg.server.port, reload=reload)


def main() -> None:
    _serve(reload=False)


def dev() -> None:
    # Dev only: autoreload, so saves apply like next dev.
    _serve(reload=True)


if __name__ == "__main__":
    main()
