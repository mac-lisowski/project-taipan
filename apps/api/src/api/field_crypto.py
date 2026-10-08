"""Composition root for the crypto module: real edges when config allows."""

from crypto import BreakerCipher, FieldCrypto
from kms import InfisicalCipher
from redis import Redis

from api.config import (
    Config,
    get_config,
)
from api.db import SessionLocal
from api.dek_cache import LocalTtlDekCache, RedisDekCache, TwoTierDekCache
from api.dek_store import PostgresDekStore
from api.models.encrypted_string import set_field_crypto


def build_field_crypto(config: Config | None = None) -> FieldCrypto | None:
    """The module, or None when Infisical config is absent (capability off)."""
    cfg = config or get_config()
    if not cfg.crypto.infisical_token or not cfg.crypto.infisical_kms_key_id:
        return None
    cipher = InfisicalCipher(cfg.crypto.infisical_url, cfg.crypto.infisical_token)
    cipher = BreakerCipher(
        cipher,
        threshold=cfg.crypto.kms_breaker_threshold,
        cooldown_seconds=cfg.crypto.kms_breaker_cooldown,
    )
    store = PostgresDekStore(SessionLocal, cfg.crypto.infisical_kms_key_id)
    cache = TwoTierDekCache(
        local=LocalTtlDekCache(cfg.crypto.dek_cache_l1_ttl),
        remote=RedisDekCache(Redis.from_url(cfg.store.redis_url), cfg.crypto.dek_cache_ttl),
    )
    return FieldCrypto(
        cipher=cipher,
        store=store,
        default_key_id=cfg.crypto.infisical_kms_key_id,
        cache=cache,
    )


def build_and_register_field_crypto(config: Config | None = None) -> FieldCrypto | None:
    """Build and hand the module to the ORM column; None when off."""
    module = build_field_crypto(config)
    set_field_crypto(module)
    return module
