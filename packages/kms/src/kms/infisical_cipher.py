"""Cipher adapter for the cryptographic-operator identity.

Exposes only encrypt and decrypt; provisioning is unreachable on
this type by construction, so a runtime token cannot name it.
"""

import base64

from kms._infisical_transport import InfisicalTransport


class InfisicalCipher:
    """Implements Cipher against the Infisical REST API."""

    def __init__(self, base_url: str, token: str) -> None:
        self._transport = InfisicalTransport(base_url, token)

    def encrypt(self, key_id: str, data: bytes) -> str:
        plaintext = base64.b64encode(data).decode()
        body = self._transport.request(
            "POST", f"/api/v1/kms/keys/{key_id}/encrypt", {"plaintext": plaintext}
        )
        return body["ciphertext"]

    def decrypt(self, key_id: str, ciphertext: str) -> bytes:
        body = self._transport.request(
            "POST", f"/api/v1/kms/keys/{key_id}/decrypt", {"ciphertext": ciphertext}
        )
        return base64.b64decode(body["plaintext"])
