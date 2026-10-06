"""KMS adapter integration tests against the live Infisical instance.

Skip when the instance is unreachable or no admin token is set, same
convention as test_infisical.py. The fixture self-provisions a KMS
project and key through the provisioner, then deletes the project on
teardown. Transport error and structural tests run everywhere because
they need no live instance.
"""

import base64
import os
import urllib.error
import urllib.request

import pytest
from kms import KmsError
from kms.infisical_cipher import InfisicalCipher
from kms.infisical_provisioner import InfisicalProvisioner

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


@live_only
def test_encrypt_decrypt_roundtrip(keys) -> None:
    plaintext = b"taipan roundtrip secret"
    ciphertext = keys.cipher.encrypt(keys.key_a, plaintext)
    assert isinstance(ciphertext, str)
    # str vs bytes compares never equal; compare against the base64 form.
    assert ciphertext != base64.b64encode(plaintext).decode()
    assert keys.cipher.decrypt(keys.key_a, ciphertext) == plaintext


@live_only
def test_decrypt_garbage_raises_kmserror(keys) -> None:
    with pytest.raises(KmsError):
        keys.cipher.decrypt(keys.key_a, "junk")


@live_only
def test_rotation_preserves_decryption(keys) -> None:
    plaintext = b"taipan rotation secret"
    old_ciphertext = keys.provisioner.encrypt(keys.key_a, plaintext)
    new_version = keys.provisioner.rotate(keys.key_a)
    # A fresh key starts at version 1, so one rotation must yield 2.
    assert new_version == 2
    assert keys.provisioner.decrypt(keys.key_a, old_ciphertext) == plaintext
    fresh = keys.provisioner.encrypt(keys.key_a, plaintext)
    assert keys.provisioner.decrypt(keys.key_a, fresh) == plaintext


@live_only
def test_cross_key_decrypt_fails(keys) -> None:
    # Only this test needs a second key, so it is created inline.
    key_b = keys.provisioner.create_key(keys.project_id, "test-key-b")
    plaintext = b"taipan cross-key secret"
    ciphertext = keys.provisioner.encrypt(keys.key_a, plaintext)
    # Pinned live: Infisical rejects wrong-key GCM auth with HTTP 500,
    # so the adapter must raise instead of returning plaintext.
    with pytest.raises(KmsError):
        keys.provisioner.decrypt(key_b, ciphertext)


@live_only
def test_provisioner_can_encrypt(keys) -> None:
    plaintext = b"taipan provisioner secret"
    ciphertext = keys.provisioner.encrypt(keys.key_a, plaintext)
    assert keys.provisioner.decrypt(keys.key_a, ciphertext) == plaintext


def test_transport_error_raises_kmserror() -> None:
    # Port 1 refuses connections, so this fails below the HTTP layer.
    provisioner = InfisicalProvisioner("http://127.0.0.1:1", "unused-token")
    with pytest.raises(KmsError):
        provisioner.decrypt("some-key-id", "junk")


def test_cipher_has_no_provisioning_methods() -> None:
    # Two-identity rule lives in the types; structural, so it never skips.
    cipher = InfisicalCipher("http://127.0.0.1:1", "unused-token")
    assert hasattr(cipher, "encrypt")
    assert hasattr(cipher, "decrypt")
    for name in ("rotate", "create_project", "create_key", "delete_project"):
        assert not hasattr(cipher, name)


def test_provisioner_exposes_both_identities() -> None:
    # The admin token may encrypt too; structural, so it never skips.
    provisioner = InfisicalProvisioner("http://127.0.0.1:1", "unused-token")
    for name in ("encrypt", "decrypt", "rotate", "create_project", "create_key", "delete_project"):
        assert hasattr(provisioner, name)


@live_only
def test_cipher_roundtrip_live(keys) -> None:
    plaintext = b"taipan cipher secret"
    ciphertext = keys.cipher.encrypt(keys.key_a, plaintext)
    assert keys.cipher.decrypt(keys.key_a, ciphertext) == plaintext


@live_only
def test_cipher_garbage_ciphertext_raises_kmserror(keys) -> None:
    with pytest.raises(KmsError):
        keys.cipher.decrypt(keys.key_a, "junk")


def test_transport_error_raises_kmserror_via_cipher() -> None:
    cipher = InfisicalCipher("http://127.0.0.1:1", "unused-token")
    with pytest.raises(KmsError):
        cipher.decrypt("some-key-id", "junk")
