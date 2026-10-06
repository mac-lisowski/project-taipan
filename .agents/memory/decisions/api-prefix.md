# FastAPI mounts routers under /api

`prefix="/api"` on `include_router` so the BFF proxy is a plain 1:1
forwarder with no path rewriting.
