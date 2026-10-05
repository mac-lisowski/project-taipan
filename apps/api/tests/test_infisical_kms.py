"""KMS client integration tests against the live Infisical instance.

Skip when the instance is unreachable or no admin token is set, same
convention as test_infisical.py. The fixture self-provisions a KMS
project and key, then deletes the project on teardown. The transport
error test runs everywhere because it needs no live instance.
"""

import base64
import os
import urllib.error
import urllib.request
import uuid
from collections.abc import Iterator
from typing import NamedTuple

import pytest
from kms import InfisicalKms, KmsError
from kms.infisical_cipher import InfisicalCipher

INFISICAL_URL = os.environ.get("API_INFISICAL_URL", "http://localhost:8080")
TOKEN = os.environ.get("API_INFISICAL_TOKEN", "")


def _reachable() -> bool:
    try:
        with urllib.request.urlopen(f"{INFISICAL_URL}/api/status", timeout=2) as r:
            return r.status == 200
    except (OSError, urllib.error.URLError):
        return False


live_only = pytest.mark.skipif(
    not _reachable() or not TOKEN, reason="infisical not reachable or token unset"
)


class Keys(NamedTuple):
    client: InfisicalKms
    cipher: InfisicalCipher
    project_id: str
    key_a: str


@pytest.fixture(scope="session")
def keys() -> Iterator[Keys]:
    client = InfisicalKms(INFISICAL_URL, TOKEN)
    cipher = InfisicalCipher(INFISICAL_URL, TOKEN)
    project_id = client.create_project(f"taipan-test-{uuid.uuid4().hex}")
    key_a = client.create_key(project_id, "test-key-a")
    yield Keys(client, cipher, project_id, key_a)
    try:
        client.delete_project(project_id)
    except KmsError as exc:
        # A lost-response retry 404s; the project is gone either way.
        if " failed: 404 " not in str(exc):
            raise


@live_only
def test_encrypt_decrypt_roundtrip(keys: Keys) -> None:
    plaintext = b"taipan roundtrip secret"
    ciphertext = keys.client.encrypt(keys.key_a, plaintext)
    assert isinstance(ciphertext, str)
    # str vs bytes compares never equal; compare against the base64 form.
    assert ciphertext != base64.b64encode(plaintext).decode()
    assert keys.client.decrypt(keys.key_a, ciphertext) == plaintext


@live_only
def test_decrypt_garbage_raises_kmserror(keys: Keys) -> None:
    with pytest.raises(KmsError):
        keys.client.decrypt(keys.key_a, "junk")


@live_only
def test_rotation_preserves_decryption(keys: Keys) -> None:
    plaintext = b"taipan rotation secret"
    old_ciphertext = keys.client.encrypt(keys.key_a, plaintext)
    new_version = keys.client.rotate(keys.key_a)
    # A fresh key starts at version 1, so one rotation must yield 2.
    assert new_version == 2
    assert keys.client.decrypt(keys.key_a, old_ciphertext) == plaintext
    fresh = keys.client.encrypt(keys.key_a, plaintext)
    assert keys.client.decrypt(keys.key_a, fresh) == plaintext


@live_only
def test_cross_key_decrypt_fails(keys: Keys) -> None:
    # Only this test needs a second key, so it is created inline.
    key_b = keys.client.create_key(keys.project_id, "test-key-b")
    plaintext = b"taipan cross-key secret"
    ciphertext = keys.client.encrypt(keys.key_a, plaintext)
    # Pinned live: Infisical rejects wrong-key GCM auth with HTTP 500,
    # so the adapter must raise instead of returning plaintext.
    with pytest.raises(KmsError):
        keys.client.decrypt(key_b, ciphertext)


def test_transport_error_raises_kmserror() -> None:
    # Port 1 refuses connections, so this fails below the HTTP layer.
    kms = InfisicalKms("http://127.0.0.1:1", "unused-token")
    with pytest.raises(KmsError):
        kms.decrypt("some-key-id", "junk")


def test_cipher_has_no_provisioning_methods() -> None:
    # Two-identity rule lives in the types; structural, so it never skips.
    cipher = InfisicalCipher("http://127.0.0.1:1", "unused-token")
    assert hasattr(cipher, "encrypt")
    assert hasattr(cipher, "decrypt")
    for name in ("rotate", "create_project", "create_key", "delete_project"):
        assert not hasattr(cipher, name)


@live_only
def test_cipher_roundtrip_live(keys: Keys) -> None:
    plaintext = b"taipan cipher secret"
    ciphertext = keys.cipher.encrypt(keys.key_a, plaintext)
    assert keys.cipher.decrypt(keys.key_a, ciphertext) == plaintext


@live_only
def test_cipher_garbage_ciphertext_raises_kmserror(keys: Keys) -> None:
    with pytest.raises(KmsError):
        keys.cipher.decrypt(keys.key_a, "junk")


def test_transport_error_raises_kmserror_via_cipher() -> None:
    cipher = InfisicalCipher("http://127.0.0.1:1", "unused-token")
    with pytest.raises(KmsError):
        cipher.decrypt("some-key-id", "junk")
