"""Infisical adapter for the KMS ports, over httpx2.

Verified against self-hosted Infisical v0.165.16. Create responses are
wrapped: workspace -> {"project": {...}}, key -> {"key": {...}}.
"""

import base64

import httpx2

from kms.errors import KmsError


class InfisicalKms:
    """Implements Cipher and Provisioning against the Infisical REST API."""

    def __init__(self, base_url: str, token: str) -> None:
        self._client = httpx2.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=15.0,
        )

    def _request(self, method: str, path: str, json: dict | None = None) -> dict:
        response = self._client.request(method, path, json=json)
        if not response.is_success:
            raise KmsError(f"{method} {path} failed: {response.status_code} {response.text}")
        return response.json()

    def encrypt(self, key_id: str, data: bytes) -> str:
        plaintext = base64.b64encode(data).decode()
        body = self._request("POST", f"/api/v1/kms/keys/{key_id}/encrypt", {"plaintext": plaintext})
        return body["ciphertext"]

    def decrypt(self, key_id: str, ciphertext: str) -> bytes:
        body = self._request(
            "POST", f"/api/v1/kms/keys/{key_id}/decrypt", {"ciphertext": ciphertext}
        )
        return base64.b64decode(body["plaintext"])

    def create_project(self, name: str) -> str:
        body = self._request("POST", "/api/v2/workspace", {"projectName": name, "type": "kms"})
        return body["project"]["id"]

    def create_key(self, project_id: str, name: str) -> str:
        body = self._request(
            "POST",
            "/api/v1/kms/keys",
            {
                "projectId": project_id,
                "name": name,
                "encryptionAlgorithm": "aes-256-gcm",
                "keyUsage": "encrypt-decrypt",
            },
        )
        return body["key"]["id"]

    def delete_project(self, project_id: str) -> None:
        self._request("DELETE", f"/api/v1/workspace/{project_id}")
