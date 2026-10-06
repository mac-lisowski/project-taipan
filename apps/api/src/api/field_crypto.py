"""Composition root for the crypto module: real edges when config allows."""

from crypto import BreakerCipher, FieldCrypto
from kms import InfisicalCipher
from redis import Redis

from api.config import (
    DEFAULT_DEK_CACHE_L1_TTL as _DEFAULT_DEK_L1,
)
from api.config import (
    DEFAULT_DEK_CACHE_TTL as _DEFAULT_DEK_TTL,
)
from api.config import (
    DEFAULT_KMS_BREAKER_COOLDOWN as _DEFAULT_KMS_COOLDOWN,
)
from api.config import (
    DEFAULT_KMS_BREAKER_THRESHOLD as _DEFAULT_KMS_THRESHOLD,
)
from api.config import (
    Config,
    get_config,
)
from api.db import SessionLocal
from api.dek_cache import LocalTtlDekCache, RedisDekCache, TwoTierDekCache
from api.dek_store import PostgresDekStore
from api.models.encrypted_string import set_field_crypto

DEFAULT_DEK_CACHE_TTL_SECONDS = _DEFAULT_DEK_TTL
DEFAULT_DEK_L1_TTL_SECONDS = _DEFAULT_DEK_L1
DEFAULT_KMS_BREAKER_THRESHOLD = _DEFAULT_KMS_THRESHOLD
DEFAULT_KMS_BREAKER_COOLDOWN_SECONDS = _DEFAULT_KMS_COOLDOWN


def build_field_crypto(config: Config | None = None) -> FieldCrypto | None:
    """The module, or None when Infisical config is absent (capability off)."""
    cfg = config or get_config()
    if not cfg.infisical_token or not cfg.infisical_kms_key_id:
        return None
    cipher = InfisicalCipher(cfg.infisical_url, cfg.infisical_token)
    cipher = BreakerCipher(
        cipher,
        threshold=cfg.kms_breaker_threshold,
        cooldown_seconds=cfg.kms_breaker_cooldown,
    )
    store = PostgresDekStore(SessionLocal, cfg.infisical_kms_key_id)
    cache = TwoTierDekCache(
        local=LocalTtlDekCache(cfg.dek_cache_l1_ttl),
        remote=RedisDekCache(Redis.from_url(cfg.redis_url), cfg.dek_cache_ttl),
    )
    return FieldCrypto(
        cipher=cipher,
        store=store,
        default_key_id=cfg.infisical_kms_key_id,
        cache=cache,
    )


def build_and_register_field_crypto(config: Config | None = None) -> FieldCrypto | None:
    """Build and hand the module to the ORM column; None when off."""
    module = build_field_crypto(config)
    set_field_crypto(module)
    return module
