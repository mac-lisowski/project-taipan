"""Request-scope middleware: tenant context and the files request-size bound."""

from collections.abc import Awaitable, Callable

from crypto import tenant_scope
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from api import sessions
from api.config import get_config

FILES_PATH_PREFIX = "/api/files"
# Multipart framing rides inside the body. The slack lets a file at exactly
# the per-purpose cap pass the coarse request bound; the service cap stays
# the precise per-file check.
ENVELOPE_SLACK = 8 * 1024


class _BodyTooLarge(Exception):
    """Internal signal: the request body crossed the configured bound."""


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


class RequestSizeLimitMiddleware:
    """Bound request bodies on the files paths by counting receive bytes.

    Pure ASGI on purpose: it must wrap ``receive``. ``Content-Length`` is
    not trusted, because the BFF strips it and forwards the body chunked.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        prefix: str = FILES_PATH_PREFIX,
        slack: int = ENVELOPE_SLACK,
    ) -> None:
        self.app = app
        self.prefix = prefix
        self.slack = slack

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope.get("path", "").startswith(self.prefix):
            await self.app(scope, receive, send)
            return
        limit = get_config().storage.upload_max_bytes + self.slack
        total = 0
        response_started = False

        async def bounded_receive() -> Message:
            nonlocal total
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > limit:
                    raise _BodyTooLarge
            return message

        async def tracked_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, bounded_receive, tracked_send)
        except _BodyTooLarge:
            # A response already in flight cannot be replaced with 413.
            if response_started:
                raise
            response = PlainTextResponse("request body too large", status_code=413)
            await response(scope, receive, send)
