"""Request tenant scope: cookie to session store to tenant_scope context."""

from collections.abc import Awaitable, Callable

from crypto import tenant_scope
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from api import sessions


class TenantScopeMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        token = request.cookies.get(sessions.COOKIE_NAME)
        tenant_id = sessions.tenant_id_for_token(token) if token else None
        if tenant_id is None:
            # Unresolvable sessions run unscoped; encrypted writes fail loud.
            return await call_next(request)
        with tenant_scope(tenant_id):
            return await call_next(request)
