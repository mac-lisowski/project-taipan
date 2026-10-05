"""Ports the crypto module needs. Swapping an edge is a new adapter."""

from typing import Protocol


class DekStore(Protocol):
    """Durable per-tenant wrapped DEKs.

    Put is get-or-create: it returns the stored value even when the
    caller's proposal lost a race, so the loser can adopt the winner.
    """

    def get(self, tenant_id: str) -> str | None: ...

    def put(self, tenant_id: str, wrapped_dek: str) -> str: ...


class DekCache(Protocol):
    """Optional cache for unwrapped DEKs. Errors here must degrade, not fail.

    A non-positive ``ttl_seconds`` defers to the adapter's configured default.
    """

    def get(self, tenant_id: str) -> bytes | None: ...

    def put(self, tenant_id: str, dek: bytes, ttl_seconds: int) -> None: ...


class KeyResolver(Protocol):
    """Tenant to KMS key id. Per-tenant keys later change only this."""

    def key_id_for(self, tenant_id: str) -> str: ...
