from core import greet
from fastapi import FastAPI

from api.routers import users_router

app = FastAPI()
app.include_router(users_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": greet("world")}


def main() -> None:
    import uvicorn

    uvicorn.run("api.main:app", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
