from contextlib import asynccontextmanager

from core import greet
from fastapi import FastAPI

from api.field_crypto import build_and_register_field_crypto
from api.models.encrypted_string import set_field_crypto
from api.routers import auth_router, profiles_router, users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Registers the crypto module when Infisical config exists; off otherwise.
    build_and_register_field_crypto()
    yield
    # A repeated lifespan in one process must not serve a stale module.
    set_field_crypto(None)


app = FastAPI(lifespan=lifespan)
app.include_router(users_router, prefix="/api")
app.include_router(profiles_router, prefix="/api")
app.include_router(auth_router, prefix="/api")


@app.get("/")
def root() -> dict[str, str]:
    return {"message": greet("world")}


def main() -> None:
    import uvicorn

    uvicorn.run("api.main:app", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
