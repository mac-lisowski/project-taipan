"""Verify that a runtime token can actually use a provisioned key.

Unit tests drive a fake cipher with an injectable failure mode, so no
live stack is needed. The hints are pinned by cause: a 401/403 means
the grant hint; any other failure means the backend hint. Neither
hint names the pinned project, which lives only in the script.
"""

import base64

from crypto.errors import CipherError
from kms.errors import KmsError
from kms.verify import BACKEND_HINT, GRANT_HINT, verify_key


class FakeCipher:
    """Base64 roundtrip; the mode picks the failure to raise."""

    def __init__(self, mode: str = "ok") -> None:
        assert mode in {"ok", "grant", "backend", "transport", "corrupt"}
        self.calls: list[tuple[str, str]] = []
        self._mode = mode

    def encrypt(self, key_id: str, data: bytes) -> str:
        self.calls.append(("encrypt", key_id))
        if self._mode == "grant":
            raise KmsError("encrypt rejected", status_code=403)
        if self._mode == "backend":
            raise KmsError("encrypt failed", status_code=503)
        if self._mode == "transport":
            raise CipherError("connection refused")
        return base64.b64encode(data).decode()

    def decrypt(self, key_id: str, ciphertext: str) -> bytes:
        self.calls.append(("decrypt", key_id))
        if self._mode == "grant":
            raise KmsError("decrypt rejected", status_code=403)
        payload = base64.b64decode(ciphertext)
        if self._mode == "corrupt":
            # A backend that mangles payloads fails the roundtrip.
            return payload + b"-mangled"
        return payload


def test_verify_key_roundtrips_and_returns_none_on_success() -> None:
    fake = FakeCipher()
    assert verify_key(fake, "key-1") is None
    assert fake.calls == [("encrypt", "key-1"), ("decrypt", "key-1")]


def test_verify_key_returns_the_grant_hint_on_a_rejection() -> None:
    hint = verify_key(FakeCipher(mode="grant"), "key-1")
    assert hint == GRANT_HINT
    assert "cryptographic-operator" in hint


def test_verify_key_returns_the_backend_hint_on_server_errors() -> None:
    hint = verify_key(FakeCipher(mode="backend"), "key-1")
    assert hint == BACKEND_HINT
    assert "API_INFISICAL_URL" in hint


def test_verify_key_returns_the_backend_hint_on_transport_failure() -> None:
    # No HTTP status exists here, so the grant must not be blamed.
    assert verify_key(FakeCipher(mode="transport"), "key-1") == BACKEND_HINT


def test_verify_key_returns_the_backend_hint_on_a_roundtrip_mismatch() -> None:
    assert verify_key(FakeCipher(mode="corrupt"), "key-1") == BACKEND_HINT


def test_hints_never_name_the_pinned_project() -> None:
    for hint in (GRANT_HINT, BACKEND_HINT):
        assert "taipan-field-encryption" not in hint
        assert "platform-field-encryption" not in hint
