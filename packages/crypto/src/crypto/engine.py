"""The deep module: tenant-first encrypt and decrypt over injected edges."""

import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from kms.ports import Cipher

from crypto.deks import DefaultKeyResolver, DekManager
from crypto.envelope import NONCE_BYTES, parse, serialize
from crypto.errors import CryptoCategory, CryptoError
from crypto.ports import DekCache, DekStore, KeyResolver


class FieldCrypto:
    """Field encryption for one tenant scope at a time.

    With no resolver, every tenant maps to ``default_key_id``. Pass a
    KeyResolver to move to per-tenant keys without touching this class.
    With no cache, every use unwraps the DEK through the Cipher port.
    """

    def __init__(
        self,
        cipher: Cipher,
        store: DekStore,
        default_key_id: str | None = None,
        resolver: KeyResolver | None = None,
        cache: DekCache | None = None,
    ) -> None:
        if resolver is not None and default_key_id is not None:
            raise ValueError("pass a resolver or a default_key_id, not both")
        self._resolver = resolver or DefaultKeyResolver(_require(default_key_id))
        self._cipher = cipher
        self._store = store
        self._cache = cache
        self._deks = DekManager(cipher, store, cache)

    @property
    def cipher(self) -> Cipher:
        return self._cipher

    @property
    def store(self) -> DekStore:
        return self._store

    @property
    def cache(self) -> DekCache | None:
        return self._cache

    def encrypt(self, tenant_id: str, plaintext: str) -> str:
        self._require_scope(tenant_id)
        key_id = self._resolver.key_id_for(tenant_id)
        dek = self._deks.get_or_create(tenant_id, key_id)
        nonce = os.urandom(NONCE_BYTES)
        ciphertext = AESGCM(dek).encrypt(nonce, plaintext.encode(), _aad(tenant_id, key_id))
        return serialize(key_id, nonce, ciphertext)

    def decrypt(self, tenant_id: str, envelope: str) -> str:
        self._require_scope(tenant_id)
        key_id, nonce, ciphertext = parse(envelope)
        dek = self._deks.decrypt_key(tenant_id, key_id)
        try:
            plaintext = AESGCM(dek).decrypt(nonce, ciphertext, _aad(tenant_id, key_id))
        except InvalidTag:
            # Wrong DEK, wrong tenant scope, or tampering all land here.
            raise CryptoError(
                CryptoCategory.DECRYPT_FAILURE, "ciphertext failed authentication"
            ) from None
        try:
            return plaintext.decode()
        except UnicodeDecodeError as exc:
            # Only reachable for a validly tagged envelope from another writer.
            raise CryptoError(
                CryptoCategory.DECRYPT_FAILURE, "decrypted bytes are not text"
            ) from exc

    @staticmethod
    def _require_scope(tenant_id: str) -> None:
        if not tenant_id:
            raise CryptoError(
                CryptoCategory.MISSING_TENANT_SCOPE, "encrypt and decrypt need a tenant"
            )


def _require(default_key_id: str | None) -> str:
    if default_key_id is None:
        raise ValueError("a resolver or a default_key_id is required")
    return default_key_id


def _aad(tenant_id: str, key_id: str) -> bytes:
    # NUL keeps tenant ids and key ids unambiguous in the bound data.
    return f"{tenant_id}\0{key_id}".encode()
