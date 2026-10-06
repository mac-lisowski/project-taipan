"""Export contract tests: the package root exposes exactly the public surface."""

import crypto
import pytest

CONTRACT_EXPORTS = {
    "NONCE_BYTES",
    # BreakerCipher stays exported: the api composition root imports it.
    "BreakerCipher",
    "CryptoCategory",
    "CryptoError",
    "DefaultKeyResolver",
    "DekCache",
    "DekStore",
    "FieldCrypto",
    "KeyResolver",
    "current_tenant",
    "parse",
    "require_tenant",
    "tenant_scope",
}


def test_dunder_all_matches_contract():
    assert set(crypto.__all__) == CONTRACT_EXPORTS


def test_internals_not_package_root_importable():
    with pytest.raises(ImportError):
        from crypto import DekManager  # noqa: F401
    with pytest.raises(ImportError):
        from crypto import tenant_ctx  # noqa: F401
