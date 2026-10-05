"""Unit tests for the crypto module. All edges are stubs; no network."""

import logging
import os
import threading

import pytest
from crypto import CryptoCategory, CryptoError, FieldCrypto
from testsupport import (
    DEFAULT_KEY_ID,
    TENANT_A,
    TENANT_B,
    FakeCipher,
    FakeDekStore,
    MapResolver,
    b64u,
    flip_ciphertext_byte,
    make_module,
)


def test_envelope_grammar_rejects_malformed() -> None:
    nonce = b64u(bytes(12))
    long_nonce = b64u(bytes(16))
    key = "5f0c9a1e-2222-4333-8444-555566667777"
    malformed = [
        "",
        "v1",
        f"v1:{key}:{nonce}",
        f"v1:{key}:{nonce}:AAAA:tail",
        f"v2:{key}:{nonce}:AAAA",
        f"v1:notauuid-2222-4333-8444-555566667777:{nonce}:AAAA",
        f"v1:{key}:{long_nonce}:AAAA",
        f"v1:{key}:{nonce}=:AAAA",
    ]
    categories: list[CryptoCategory] = []
    for envelope in malformed:
        with pytest.raises(CryptoError) as raised:
            make_module().decrypt(TENANT_A, envelope)
        categories.append(raised.value.category)
    assert categories == [CryptoCategory.ENVELOPE_GRAMMAR] * len(malformed)


def test_roundtrip_returns_plaintext() -> None:
    module = make_module()
    envelope = module.encrypt(TENANT_A, "alpha secret")
    assert envelope.startswith("v1:")
    assert module.decrypt(TENANT_A, envelope) == "alpha secret"


def test_cross_tenant_decrypt_fails() -> None:
    cipher = FakeCipher()
    winner_wrapped = cipher.encrypt(DEFAULT_KEY_ID, os.urandom(32))
    # The rigged store gives both tenants the same DEK, so only the
    # associated data can tell the scopes apart.
    store = FakeDekStore(conflict_wrapped=winner_wrapped)
    module = make_module(store=store, cipher=cipher)
    a_envelope = module.encrypt(TENANT_A, "alpha secret")
    module.encrypt(TENANT_B, "beta seed")
    with pytest.raises(CryptoError) as raised:
        module.decrypt(TENANT_B, a_envelope)
    assert raised.value.category is CryptoCategory.DECRYPT_FAILURE


def test_tampered_ciphertext_fails() -> None:
    module = make_module()
    envelope = module.encrypt(TENANT_A, "alpha secret")
    with pytest.raises(CryptoError) as raised:
        module.decrypt(TENANT_A, flip_ciphertext_byte(envelope))
    assert raised.value.category is CryptoCategory.DECRYPT_FAILURE


def test_resolver_falls_back_to_default_key() -> None:
    own_key_id = "9d2b7f60-3333-4444-8555-666677778888"
    resolver = MapResolver(DEFAULT_KEY_ID, {TENANT_B: own_key_id})
    module = make_module(resolver=resolver)
    assert module.encrypt(TENANT_A, "alpha").split(":")[1] == DEFAULT_KEY_ID
    assert module.encrypt(TENANT_B, "beta").split(":")[1] == own_key_id


def test_constructor_rejects_resolver_and_default_key_together() -> None:
    # Two key sources would disagree silently; the constructor refuses.
    with pytest.raises(ValueError):
        FieldCrypto(
            cipher=FakeCipher(),
            store=FakeDekStore(),
            default_key_id=DEFAULT_KEY_ID,
            resolver=MapResolver(DEFAULT_KEY_ID, {}),
        )


def test_single_flight_unwraps_once() -> None:
    cipher, store = FakeCipher(unwrap_delay=0.05), FakeDekStore()
    seeder = make_module(store=store, cipher=cipher)
    envelope = seeder.encrypt(TENANT_A, "alpha secret")
    cold = make_module(store=store, cipher=cipher)
    results: list[str] = []
    errors: list[Exception] = []
    barrier = threading.Barrier(8)

    def worker() -> None:
        barrier.wait()
        try:
            results.append(cold.decrypt(TENANT_A, envelope))
        except Exception as exc:  # noqa: BLE001 - collected and asserted below
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []
    assert results == ["alpha secret"] * 8
    assert cipher.unwrap_calls == 1


def test_failed_unwrap_is_not_cached() -> None:
    cipher, store = FakeCipher(), FakeDekStore()
    envelope = make_module(store=store, cipher=cipher).encrypt(TENANT_A, "alpha secret")
    cold = make_module(store=store, cipher=cipher)
    cipher.unwrap_failures_left = 1
    with pytest.raises(CryptoError) as raised:
        cold.decrypt(TENANT_A, envelope)
    assert raised.value.category is CryptoCategory.DECRYPT_FAILURE
    assert cipher.unwrap_calls == 1
    assert cold.decrypt(TENANT_A, envelope) == "alpha secret"
    assert cipher.unwrap_calls == 2


def test_put_race_adopts_stored_dek() -> None:
    cipher = FakeCipher()
    winner_wrapped = cipher.encrypt(DEFAULT_KEY_ID, os.urandom(32))
    store = FakeDekStore(conflict_wrapped=winner_wrapped)
    # Two instances stand in for two racing processes sharing one store.
    first = make_module(store=store, cipher=cipher)
    second = make_module(store=store, cipher=cipher)
    one = first.encrypt(TENANT_A, "one")
    two = second.encrypt(TENANT_A, "two")
    assert store.rows[TENANT_A] == winner_wrapped
    assert store.put_calls == 1
    assert first.decrypt(TENANT_A, two) == "two"
    assert second.decrypt(TENANT_A, one) == "one"


def test_missing_dek_row_raises_unknown_dek() -> None:
    store = FakeDekStore()
    envelope = f"v1:{DEFAULT_KEY_ID}:{b64u(os.urandom(12))}:{b64u(os.urandom(32))}"
    with pytest.raises(CryptoError) as raised:
        make_module(store=store).decrypt(TENANT_A, envelope)
    assert raised.value.category is CryptoCategory.UNKNOWN_DEK


def test_errors_carry_no_key_material() -> None:
    module = make_module()
    envelope = module.encrypt(TENANT_A, "alpha secret")
    _version, key_id, nonce, ciphertext = envelope.split(":")
    secrets = [key_id, nonce, ciphertext, "alpha secret", "unwrap rejected by the backend"]
    cold = make_module()
    cipher = FakeCipher()
    cipher.unwrap_failures_left = 1
    shared_store = FakeDekStore()
    seeded = make_module(store=shared_store, cipher=cipher)
    seeded_envelope = seeded.encrypt(TENANT_A, "alpha secret")

    with pytest.raises(CryptoError) as raised:
        module.decrypt(TENANT_A, "not-an-envelope")
    grammar_error = raised.value
    with pytest.raises(CryptoError) as raised:
        module.decrypt(TENANT_A, flip_ciphertext_byte(envelope))
    tamper_error = raised.value
    with pytest.raises(CryptoError) as raised:
        cold.decrypt(TENANT_A, envelope)
    unknown_dek_error = raised.value
    with pytest.raises(CryptoError) as raised:
        make_module(store=shared_store, cipher=cipher).decrypt(TENANT_A, seeded_envelope)
    unwrap_error = raised.value

    errors = [grammar_error, tamper_error, unknown_dek_error, unwrap_error]
    assert [error.category for error in errors] == [
        CryptoCategory.ENVELOPE_GRAMMAR,
        CryptoCategory.DECRYPT_FAILURE,
        CryptoCategory.UNKNOWN_DEK,
        CryptoCategory.DECRYPT_FAILURE,
    ]
    assert all(secret not in str(error) for error in errors for secret in secrets)


def test_cache_hit_after_first_use() -> None:
    cipher, store = FakeCipher(), FakeDekStore()
    module = make_module(store=store, cipher=cipher)
    envelope = module.encrypt(TENANT_A, "one")
    assert cipher.wrap_calls == 1
    module.encrypt(TENANT_A, "two")
    assert module.decrypt(TENANT_A, envelope) == "one"
    assert cipher.wrap_calls == 1
    assert cipher.unwrap_calls == 0
    assert store.get_calls == 1
    assert store.put_calls == 1


def test_broken_cache_degrades_with_a_warning(caplog) -> None:
    # Not the Redis adapter: the manager itself must degrade and log.
    class ExplodingCache:
        def get(self, tenant_id: str) -> bytes:
            raise RuntimeError("cache down")

        def put(self, tenant_id: str, dek: bytes) -> None:
            raise RuntimeError("cache down")

    module = FieldCrypto(
        cipher=FakeCipher(),
        store=FakeDekStore(),
        default_key_id=DEFAULT_KEY_ID,
        cache=ExplodingCache(),
    )
    with caplog.at_level(logging.WARNING):
        envelope = module.encrypt(TENANT_A, "alpha secret")
        assert module.decrypt(TENANT_A, envelope) == "alpha secret"
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert "dek cache read failed; continuing without the cache" in warnings
    assert "dek cache write failed; continuing without the cache" in warnings
    assert "alpha secret" not in caplog.text
