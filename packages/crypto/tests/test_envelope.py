"""Envelope write-path grammar: serialize enforces the key-id rule. No edges."""

import os

import pytest
from crypto import CryptoCategory, CryptoError
from crypto.envelope import parse, serialize


def test_serialize_rejects_non_uuid_key_id() -> None:
    nonce, ciphertext = os.urandom(12), os.urandom(32)
    for key_id in ("", "not-a-uuid", "kms-key-alias", "5f0c9a1e_2222_4333_8444_555566667777"):
        with pytest.raises(CryptoError) as raised:
            serialize(key_id, nonce, ciphertext)
        assert raised.value.category is CryptoCategory.ENVELOPE_GRAMMAR


def test_serialize_parse_roundtrip_on_valid_key_id() -> None:
    key_id = "5f0c9a1e-2222-4333-8444-555566667777"
    nonce, ciphertext = os.urandom(12), os.urandom(32)
    envelope = serialize(key_id, nonce, ciphertext)
    assert parse(envelope) == (key_id, nonce, ciphertext)
