"""ORM column type that stores only crypto-module ciphertext.

Delegation only: the module does the encryption, the context carries
the tenant. Rule: one tenant scope per flush. The column reads the
tenant context at flush time, not at add() time, so rows added under
different scopes in one session all encrypt under the last scope.
Per-request scoping holds the rule naturally; background jobs must
set the scope per unit of work.
"""

from typing import Any

from crypto import require_tenant
from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

_field_crypto: Any = None


def set_field_crypto(module: Any) -> None:
    """Register the crypto module the column delegates to; None unregisters."""
    global _field_crypto
    _field_crypto = module


def get_field_crypto() -> Any:
    """The registered module, for fixtures that must restore registration."""
    return _field_crypto


def _require_module() -> Any:
    if _field_crypto is None:
        # Unregistered is a wiring error, not a crypto failure mode.
        raise RuntimeError("no crypto module is registered for EncryptedString")
    return _field_crypto


class EncryptedString(TypeDecorator[str]):
    """Plaintext in the ORM, versioned envelope in the database."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Any) -> str | None:
        if value is None:
            return None
        return _require_module().encrypt(require_tenant(), value)

    def process_result_value(self, value: str | None, dialect: Any) -> str | None:
        if value is None:
            return None
        return _require_module().decrypt(require_tenant(), value)
