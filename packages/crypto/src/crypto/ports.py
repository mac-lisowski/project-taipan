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
    """Optional cache for unwrapped DEKs. Errors here must degrade, not fail."""

    def get(self, tenant_id: str) -> bytes | None: ...

    def put(self, tenant_id: str, dek: bytes) -> None: ...


class Cipher(Protocol):
    """Key wrapping/unwrapping over a provider.

    Implementations raise ``CipherError`` on provider failure; the
    breaker counts exactly that type.
    """

    def encrypt(self, key_id: str, data: bytes) -> str: ...

    def decrypt(self, key_id: str, ciphertext: str) -> bytes: ...


class KeyResolver(Protocol):
    """Tenant to KMS key id. Per-tenant keys later change only this."""

    def key_id_for(self, tenant_id: str) -> str: ...
