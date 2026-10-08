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
        sess = sessions.resolve(token) if token else None
        if token:
            sessions.remember_resolved_session(request, token, sess)
        tenant_id = sess.tenant_id if sess is not None else None
        if tenant_id is None:
            # Unresolvable sessions run unscoped; encrypted writes fail loud.
            return await call_next(request)
        with tenant_scope(tenant_id):
            return await call_next(request)
