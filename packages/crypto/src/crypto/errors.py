"""One error type for the package, with stable category codes.

Messages never carry key ids, nonces, ciphertext, or plaintext.
"""

from enum import Enum


class CryptoCategory(str, Enum):
    """Stable codes callers branch on; new codes may appear, none change."""

    ENVELOPE_GRAMMAR = "envelope_grammar"
    DECRYPT_FAILURE = "decrypt_failure"
    WRAP_FAILURE = "wrap_failure"
    MISSING_TENANT_SCOPE = "missing_tenant_scope"
    UNKNOWN_DEK = "unknown_dek"
    KMS_UNAVAILABLE = "kms_unavailable"


class CryptoError(Exception):
    """A field-encryption failure."""

    def __init__(self, category: CryptoCategory, message: str) -> None:
        super().__init__(message)
        self.category = category
        self.message = message
