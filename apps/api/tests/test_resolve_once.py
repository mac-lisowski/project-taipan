"""One resolve per request: middleware and authz share the session read."""

from api import authz, sessions
from api.kvstore import SESSION_KEYS, MemoryKVStore, set_session_store
from api.middleware import TenantScopeMiddleware
from starlette.requests import Request
from starlette.responses import Response


class CountingStore(MemoryKVStore):
    """Counts KV gets: one resolve costs exactly two gets."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.gets = 0

    def get(self, key: str) -> str | None:
        self.gets += 1
        return super().get(key)


def _request_with_cookie(token: str) -> Request:
    return Request({"type": "http", "headers": [(b"cookie", f"session={token}".encode())]})


async def _dispatch(request: Request) -> Response:
    async def call_next(req: Request) -> Response:
        return Response("ok")

    return await TenantScopeMiddleware(app=None).dispatch(request, call_next)  # type: ignore[arg-type]


def test_middleware_and_authz_share_one_resolve(memory_session_store) -> None:
    store = CountingStore(SESSION_KEYS)
    token = sessions.mint(41, "t-41", store=store)
    store.gets = 0  # mint reads the epoch once; count only request resolves
    set_session_store(store)
    try:
        request = _request_with_cookie(token)
        import asyncio

        asyncio.run(_dispatch(request))
        assert store.gets == 2
        assert authz.resolve_session(request) is not None
        assert store.gets == 2
    finally:
        set_session_store(memory_session_store)


def test_resolve_session_without_middleware_still_resolves(memory_session_store) -> None:
    token = sessions.mint(42, "t-42", store=memory_session_store)
    data = authz.resolve_session(_request_with_cookie(token))
    assert data is not None
    assert data.user_id == 42


def test_changed_cookie_ignores_stale_cache(memory_session_store) -> None:
    first = sessions.mint(43, "t-43", store=memory_session_store)
    second = sessions.mint(44, "t-44", store=memory_session_store)
    request = _request_with_cookie(first)
    import asyncio

    asyncio.run(_dispatch(request))
    tampered = _request_with_cookie(second)
    tampered.state.__dict__.update(request.state.__dict__)
    assert authz.resolve_session(tampered) is not None
    assert authz.resolve_session(tampered).user_id == 44
