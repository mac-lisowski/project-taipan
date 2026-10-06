"""Tenant scope for call sites that carry no tenant argument, e.g. an ORM column."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from crypto.errors import CryptoCategory, CryptoError

tenant_ctx: ContextVar[str | None] = ContextVar("crypto_tenant", default=None)


@contextmanager
def tenant_scope(tenant_id: str) -> Iterator[None]:
    token = tenant_ctx.set(tenant_id)
    try:
        yield
    finally:
        tenant_ctx.reset(token)


def current_tenant() -> str | None:
    return tenant_ctx.get()


def require_tenant() -> str:
    tenant = current_tenant()
    if tenant is None:
        raise CryptoError(CryptoCategory.MISSING_TENANT_SCOPE, "no tenant scope is set")
    return tenant
