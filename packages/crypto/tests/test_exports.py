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


def _import_from_root(name: str):
    """The from-import failure path: missing root attr -> ImportError."""
    import importlib

    module = importlib.import_module("crypto")
    try:
        return getattr(module, name)
    except AttributeError as exc:
        raise ImportError(f"cannot import name {name!r} from 'crypto'") from exc


def test_internals_not_package_root_importable():
    with pytest.raises(ImportError):
        _import_from_root("DekManager")
    with pytest.raises(ImportError):
        _import_from_root("tenant_ctx")
