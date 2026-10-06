"""Per-tenant DEK lifecycle: get-or-create with conflict adoption, single-flight unwrap.

The store, the cache, and the unwrap lock are all keyed by tenant id:
the DEK belongs to the tenant, so the tenant is the unit of duplication.
"""

import logging
import threading

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from kms import KmsError
from kms.ports import Cipher

from crypto.errors import CryptoCategory, CryptoError
from crypto.ports import DekCache, DekStore

_log = logging.getLogger(__name__)


class DefaultKeyResolver:
    """Maps every tenant to one configured key id until per-tenant keys land."""

    def __init__(self, default_key_id: str) -> None:
        self._default_key_id = default_key_id

    def key_id_for(self, tenant_id: str) -> str:
        return self._default_key_id


class _NullDekCache:
    """The absent cache: every use unwraps, never retains key material."""

    def get(self, tenant_id: str) -> bytes | None:
        return None

    def put(self, tenant_id: str, dek: bytes) -> None:
        return


_LOCK_COUNT = 32


class DekManager:
    """Owns DEK material so the encrypt/decrypt engine stays free of policy."""

    def __init__(
        self,
        cipher: Cipher,
        store: DekStore,
        cache: DekCache | None = None,
    ) -> None:
        self._cipher = cipher
        self._store = store
        self._cache: DekCache = cache if cache is not None else _NullDekCache()
        self._locks = tuple(threading.Lock() for _ in range(_LOCK_COUNT))

    def get_or_create(self, tenant_id: str, key_id: str) -> bytes:
        dek = self._cache_get(tenant_id)
        if dek is not None:
            return dek
        wrapped = self._store.get(tenant_id)
        if wrapped is None:
            dek = AESGCM.generate_key(256)
            proposed = self._wrap(key_id, dek)
            stored = self._store.put(tenant_id, proposed)
            if stored != proposed:
                # The row already belongs to another caller: adopt or lose data.
                return self.unwrap(tenant_id, key_id, stored)
            self._cache_put(tenant_id, dek)
            return dek
        return self.unwrap(tenant_id, key_id, wrapped)

    def decrypt_key(self, tenant_id: str, key_id: str) -> bytes:
        dek = self._cache_get(tenant_id)
        if dek is not None:
            return dek
        wrapped = self._store.get(tenant_id)
        if wrapped is None:
            raise CryptoError(CryptoCategory.UNKNOWN_DEK, "no data key exists for this tenant")
        return self.unwrap(tenant_id, key_id, wrapped)

    def unwrap(self, tenant_id: str, key_id: str, wrapped: str) -> bytes:
        dek = self._cache_get(tenant_id)
        if dek is not None:
            return dek
        with self._lock_for(tenant_id):
            dek = self._cache_get(tenant_id)
            if dek is None:
                try:
                    dek = self._cipher.decrypt(key_id, wrapped)
                except KmsError:
                    # The Cipher message may carry backend detail; keep it out.
                    raise CryptoError(
                        CryptoCategory.DECRYPT_FAILURE,
                        "the data key could not be unwrapped",
                    ) from None
                # A failed unwrap raised above, so failures are never cached.
                self._cache_put(tenant_id, dek)
            return dek

    def _wrap(self, key_id: str, dek: bytes) -> str:
        try:
            return self._cipher.encrypt(key_id, dek)
        except KmsError:  # a wrap failure is not a decrypt failure
            raise CryptoError(
                CryptoCategory.WRAP_FAILURE, "the data key could not be wrapped"
            ) from None

    def _cache_get(self, tenant_id: str) -> bytes | None:
        try:
            return self._cache.get(tenant_id)
        except Exception:  # noqa: BLE001 - any cache backend error must degrade
            # The adapter usually logs; this catches non-adapter caches too.
            _log.warning("dek cache read failed; continuing without the cache")
            return None

    def _cache_put(self, tenant_id: str, dek: bytes) -> None:
        try:
            self._cache.put(tenant_id, dek)
        except Exception:  # noqa: BLE001 - degrade, never fail the operation
            _log.warning("dek cache write failed; continuing without the cache")

    def _lock_for(self, tenant_id: str) -> threading.Lock:
        # Stripes bound memory; sharing a lock across tenants only adds waiting.
        return self._locks[hash(tenant_id) % _LOCK_COUNT]
