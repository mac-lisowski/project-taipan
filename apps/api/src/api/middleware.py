"""Request tenant scope: cookie to session to user_tenants link."""

from collections.abc import Awaitable, Callable

from crypto import tenant_scope
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from api import db as db_module
from api import sessions


class TenantScopeMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        token = request.cookies.get(sessions.COOKIE_NAME)
        tenant_id = None
        if token is not None:
            # One short-lived session resolves scope, then closes.
            with db_module.SessionLocal() as db:
                tenant_id = sessions.tenant_id_for_token(db, token)
        if tenant_id is None:
            # Unresolvable sessions run unscoped; encrypted writes fail loud.
            return await call_next(request)
        with tenant_scope(tenant_id):
            return await call_next(request)
