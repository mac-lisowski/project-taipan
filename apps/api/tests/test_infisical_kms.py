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
    project_id: str
    key_a: str


@pytest.fixture(scope="session")
def keys() -> Iterator[Keys]:
    client = InfisicalKms(INFISICAL_URL, TOKEN)
    project_id = client.create_project(f"taipan-test-{uuid.uuid4().hex}")
    key_a = client.create_key(project_id, "test-key-a")
    yield Keys(client, project_id, key_a)
    client.delete_project(project_id)


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
