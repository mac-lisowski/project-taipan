"""Composition root for the crypto module: real edges when config allows."""

import os

from crypto import BreakerCipher, FieldCrypto
from kms import InfisicalCipher
from redis import Redis

from api.db import SessionLocal
from api.dek_cache import LocalTtlDekCache, RedisDekCache, TwoTierDekCache
from api.dek_store import PostgresDekStore
from api.models.encrypted_string import set_field_crypto

DEFAULT_DEK_CACHE_TTL_SECONDS = 900
DEFAULT_DEK_L1_TTL_SECONDS = 60
DEFAULT_KMS_BREAKER_THRESHOLD = 3
DEFAULT_KMS_BREAKER_COOLDOWN_SECONDS = 30.0


def build_field_crypto() -> FieldCrypto | None:
    """The module, or None when Infisical config is absent (capability off)."""
    token = os.environ.get("API_INFISICAL_TOKEN", "")
    key_id = os.environ.get("API_INFISICAL_KMS_KEY_ID", "")
    if not token or not key_id:
        return None
    cipher = InfisicalCipher(os.environ.get("API_INFISICAL_URL", "http://localhost:8080"), token)
    threshold = int(os.environ.get("API_KMS_BREAKER_THRESHOLD", str(DEFAULT_KMS_BREAKER_THRESHOLD)))
    if threshold < 1:
        raise ValueError("API_KMS_BREAKER_THRESHOLD must be at least 1")
    cooldown = float(
        os.environ.get("API_KMS_BREAKER_COOLDOWN", str(DEFAULT_KMS_BREAKER_COOLDOWN_SECONDS))
    )
    if cooldown <= 0:
        raise ValueError("API_KMS_BREAKER_COOLDOWN must be positive")
    cipher = BreakerCipher(cipher, threshold=threshold, cooldown_seconds=cooldown)
    store = PostgresDekStore(SessionLocal, key_id)
    ttl = int(os.environ.get("API_DEK_CACHE_TTL", str(DEFAULT_DEK_CACHE_TTL_SECONDS)))
    if ttl < 1:
        # A non-positive TTL would silently disable every cache write.
        raise ValueError("API_DEK_CACHE_TTL must be at least 1 second")
    l1_ttl = int(os.environ.get("API_DEK_CACHE_L1_TTL", str(DEFAULT_DEK_L1_TTL_SECONDS)))
    if l1_ttl < 1:
        raise ValueError("API_DEK_CACHE_L1_TTL must be at least 1 second")
    cache = TwoTierDekCache(
        local=LocalTtlDekCache(l1_ttl),
        remote=RedisDekCache(
            Redis.from_url(os.environ.get("API_REDIS_URL", "redis://localhost:6379/0")), ttl
        ),
    )
    return FieldCrypto(cipher=cipher, store=store, default_key_id=key_id, cache=cache)


def build_and_register_field_crypto() -> FieldCrypto | None:
    """Build and hand the module to the ORM column; None when off."""
    module = build_field_crypto()
    set_field_crypto(module)
    return module
