"""Provisioning-plus-cipher adapter for the admin identity.

The admin token may encrypt too, so this adapter carries both ports
over the shared transport. Verified against self-hosted Infisical
v0.165.16: create and rotate responses come back wrapped.
"""

import base64

from kms._infisical_transport import InfisicalTransport
from kms.errors import KmsError


class InfisicalProvisioner:
    """Implements Cipher and Provisioning against the Infisical REST API."""

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

    def create_project(self, name: str) -> str:
        body = self._transport.request(
            "POST", "/api/v2/workspace", {"projectName": name, "type": "kms"}
        )
        return body["project"]["id"]

    def find_project(self, name: str) -> str | None:
        # The list is membership-scoped, so only the adapter sees the
        # raw names; ambiguity must fail loud here, not pick silently.
        body = self._transport.request("GET", "/api/v1/projects?type=kms")
        matches = [p["id"] for p in body["projects"] if p["name"] == name]
        if len(matches) > 1:
            raise KmsError(
                f"find_project: {len(matches)} kms projects named {name}; clean up duplicates"
            )
        return matches[0] if matches else None

    def create_key(self, project_id: str, name: str) -> str:
        body = self._transport.request(
            "POST",
            "/api/v1/kms/keys",
            {
                "projectId": project_id,
                "name": name,
                "algorithm": "aes-256-gcm",
                "keyUsage": "encrypt-decrypt",
                "isExportable": False,
                "hasDeleteProtection": True,
            },
        )
        return body["key"]["id"]

    def find_key(self, project_id: str, name: str) -> str | None:
        # The transport has no query params, so the filter rides in the path.
        path = f"/api/v1/kms/keys/key-name/{name}?projectId={project_id}"
        try:
            body = self._transport.request("GET", path)
        except KmsError as exc:
            # Absent key is the 404 case, not a transport failure.
            if exc.status_code == 404:
                return None
            raise
        return body["key"]["id"]

    def delete_project(self, project_id: str) -> None:
        self._transport.request("DELETE", f"/api/v1/workspace/{project_id}")

    def rotate(self, key_id: str) -> int:
        # Ops-only action: the key object comes back wrapped, like create.
        body = self._transport.request("POST", f"/api/v1/kms/keys/{key_id}/rotate")
        return body["key"]["version"]
