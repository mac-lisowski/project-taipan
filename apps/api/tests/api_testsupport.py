"""Shared fakes and constants for the api tests. No network, no real KMS."""

import base64
import uuid

KEY_ID = "5f0c9a1e-2222-4333-8444-555566667777"


def unique_tenant() -> str:
    # Rows survive across session-scoped tests; a fresh tenant isolates each.
    return uuid.uuid4().hex


class StubCipher:
    """Base64 wrap/unwrap, so the degrade test needs no backend."""

    def encrypt(self, key_id: str, data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode().rstrip("=")

    def decrypt(self, key_id: str, ciphertext: str) -> bytes:
        return base64.urlsafe_b64decode(ciphertext + "=" * (-len(ciphertext) % 4))


class MapStore:
    """In-memory DekStore stand-in, so the degrade test needs no database."""

    def __init__(self) -> None:
        self.rows: dict[str, str] = {}

    def get(self, tenant_id: str) -> str | None:
        return self.rows.get(tenant_id)

    def put(self, tenant_id: str, wrapped_dek: str) -> str:
        self.rows[tenant_id] = wrapped_dek
        return wrapped_dek
