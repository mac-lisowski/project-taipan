"""Strict v1 envelope grammar: ``v1:<key_id>:<nonce>:<ciphertext>``.

Every grammar check lives here so encrypt and decrypt share one parser.
"""

import base64
import binascii
import uuid

from crypto.errors import CryptoCategory, CryptoError

_VERSION = "v1"
NONCE_BYTES = 12
_B64_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
_UUID_CHARS = frozenset("0123456789abcdefABCDEF-")


def encode(data: bytes) -> str:
    """Unpadded urlsafe base64, the only encoding the envelope allows."""
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def parse(envelope: str) -> tuple[str, bytes, bytes]:
    """Return (key_id, nonce, ciphertext) or raise the grammar error."""
    parts = envelope.split(":")
    if len(parts) != 4:
        _reject()
    version, key_id, nonce_b64, ciphertext_b64 = parts
    if version != _VERSION or not _is_uuid(key_id):
        _reject()
    nonce = _decode(nonce_b64)
    ciphertext = _decode(ciphertext_b64)
    if len(nonce) != NONCE_BYTES:
        _reject()
    return key_id, nonce, ciphertext


def serialize(key_id: str, nonce: bytes, ciphertext: bytes) -> str:
    return f"{_VERSION}:{key_id}:{encode(nonce)}:{encode(ciphertext)}"


def _reject() -> None:
    raise CryptoError(CryptoCategory.ENVELOPE_GRAMMAR, "envelope does not match the v1 grammar")


def _is_uuid(key_id: str) -> bool:
    if not key_id or not set(key_id) <= _UUID_CHARS:
        return False
    try:
        uuid.UUID(key_id)
    except ValueError:
        return False
    return True


def _decode(field: str) -> bytes:
    if not field or not set(field) <= _B64_CHARS:
        _reject()
    try:
        return base64.b64decode(field + "=" * (-len(field) % 4), altchars=b"-_", validate=True)
    except (binascii.Error, ValueError):
        _reject()
