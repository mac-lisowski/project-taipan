"""Tenant-aware field encryption over injected edges."""

from crypto.context import current_tenant, require_tenant, tenant_ctx, tenant_scope
from crypto.deks import DefaultKeyResolver, DekManager
from crypto.engine import FieldCrypto
from crypto.envelope import NONCE_BYTES, parse
from crypto.errors import CryptoCategory, CryptoError
from crypto.ports import DekCache, DekStore, KeyResolver

__all__ = [
    "NONCE_BYTES",
    "CryptoCategory",
    "CryptoError",
    "DefaultKeyResolver",
    "DekCache",
    "DekManager",
    "DekStore",
    "FieldCrypto",
    "KeyResolver",
    "current_tenant",
    "parse",
    "require_tenant",
    "tenant_ctx",
    "tenant_scope",
]
