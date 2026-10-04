"""KMS client integration tests against the live Infisical instance.

Skip when the instance is unreachable or no admin token is set, same
convention as test_infisical.py. The fixture self-provisions a KMS
project and key, then deletes the project on teardown.
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


pytestmark = pytest.mark.skipif(
    not _reachable() or not TOKEN, reason="infisical not reachable or token unset"
)


class Keys(NamedTuple):
    project_id: str
    a: str
    b: str


@pytest.fixture(scope="session")
def keys() -> Iterator[Keys]:
    kms = InfisicalKms(INFISICAL_URL, TOKEN)
    project_id = kms.create_project(f"taipan-test-{uuid.uuid4().hex}")
    key_a = kms.create_key(project_id, "test-key-a")
    key_b = kms.create_key(project_id, "test-key-b")
    yield Keys(project_id, key_a, key_b)
    kms.delete_project(project_id)


def test_encrypt_decrypt_roundtrip(keys: Keys) -> None:
    kms = InfisicalKms(INFISICAL_URL, TOKEN)
    plaintext = b"taipan roundtrip secret"
    ciphertext = kms.encrypt(keys.a, plaintext)
    assert isinstance(ciphertext, str)
    # str vs bytes compares never equal; compare against the base64 form.
    assert ciphertext != base64.b64encode(plaintext).decode()
    assert kms.decrypt(keys.a, ciphertext) == plaintext


def test_decrypt_garbage_raises_kmserror(keys: Keys) -> None:
    kms = InfisicalKms(INFISICAL_URL, TOKEN)
    with pytest.raises(KmsError):
        kms.decrypt(keys.a, "junk")


def test_rotation_preserves_decryption(keys: Keys) -> None:
    kms = InfisicalKms(INFISICAL_URL, TOKEN)
    plaintext = b"taipan rotation secret"
    old_ciphertext = kms.encrypt(keys.a, plaintext)
    new_version = kms.rotate(keys.a)
    # A fresh key starts at version 1, so one rotation must yield 2.
    assert new_version == 2
    assert kms.decrypt(keys.a, old_ciphertext) == plaintext
    assert kms.decrypt(keys.a, kms.encrypt(keys.a, plaintext)) == plaintext


def test_cross_key_decrypt_fails(keys: Keys) -> None:
    kms = InfisicalKms(INFISICAL_URL, TOKEN)
    plaintext = b"taipan cross-key secret"
    ciphertext = kms.encrypt(keys.a, plaintext)
    # Pinned live: Infisical rejects wrong-key GCM auth with HTTP 500,
    # so the adapter must raise instead of returning plaintext.
    with pytest.raises(KmsError):
        kms.decrypt(keys.b, ciphertext)
