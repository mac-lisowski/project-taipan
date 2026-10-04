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


@pytest.fixture(scope="session")
def key_id() -> Iterator[str]:
    kms = InfisicalKms(INFISICAL_URL, TOKEN)
    project_id = kms.create_project(f"taipan-test-{uuid.uuid4().hex}")
    yield kms.create_key(project_id, "test-key")
    kms.delete_project(project_id)


def test_encrypt_decrypt_roundtrip(key_id: str) -> None:
    kms = InfisicalKms(INFISICAL_URL, TOKEN)
    plaintext = b"taipan roundtrip secret"
    ciphertext = kms.encrypt(key_id, plaintext)
    assert isinstance(ciphertext, str)
    # str vs bytes compares never equal; compare against the base64 form.
    assert ciphertext != base64.b64encode(plaintext).decode()
    assert kms.decrypt(key_id, ciphertext) == plaintext


def test_decrypt_garbage_raises_kmserror(key_id: str) -> None:
    kms = InfisicalKms(INFISICAL_URL, TOKEN)
    with pytest.raises(KmsError):
        kms.decrypt(key_id, "junk")
