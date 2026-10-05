"""Private Infisical HTTP transport shared by the KMS adapters.

Not exported from the package: call sites see ports and adapters
only. Verified against self-hosted Infisical v0.165.16.
"""

import httpx2

from kms.errors import KmsError


class InfisicalTransport:
    """Carries auth, timeout, request plumbing, and error mapping."""

    def __init__(self, base_url: str, token: str) -> None:
        self._client = httpx2.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=15.0,
        )

    def request(self, method: str, path: str, json: dict | None = None) -> dict:
        try:
            response = self._client.request(method, path, json=json)
        except httpx2.HTTPError as exc:
            # Callers get one error type; they never inspect HTTP internals.
            raise KmsError(f"{method} {path} failed: {type(exc).__name__}: {exc}") from exc
        if not response.is_success:
            raise KmsError(f"{method} {path} failed: {response.status_code} {response.text}")
        return response.json()
