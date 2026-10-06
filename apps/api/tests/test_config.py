"""Tests for centralized configuration module."""

import pytest
from api.config import (
    DEFAULT_DATABASE_URL,
    DEFAULT_DEK_CACHE_L1_TTL,
    DEFAULT_DEK_CACHE_TTL,
    DEFAULT_HOST,
    DEFAULT_INFISICAL_URL,
    DEFAULT_KMS_BREAKER_COOLDOWN,
    DEFAULT_KMS_BREAKER_THRESHOLD,
    DEFAULT_PORT,
    DEFAULT_REDIS_URL,
    DEFAULT_SESSION_TTL_SECONDS,
    DEFAULT_TEST_ADMIN_URL,
    DEFAULT_TEST_URL,
    Config,
    get_config,
)

VALID_UUID = "5f0c9a1e-2222-4333-8444-555566667777"


def test_config_defaults() -> None:
    cfg = Config.from_env({})
    assert cfg.database_url == DEFAULT_DATABASE_URL
    assert cfg.test_admin_url == DEFAULT_TEST_ADMIN_URL
    assert cfg.test_database_url == DEFAULT_TEST_URL
    assert cfg.redis_url == DEFAULT_REDIS_URL
    assert cfg.dek_cache_ttl == DEFAULT_DEK_CACHE_TTL
    assert cfg.dek_cache_l1_ttl == DEFAULT_DEK_CACHE_L1_TTL
    assert cfg.infisical_url == DEFAULT_INFISICAL_URL
    assert cfg.infisical_token == ""
    assert cfg.infisical_kms_key_id == ""
    assert cfg.kms_breaker_threshold == DEFAULT_KMS_BREAKER_THRESHOLD
    assert cfg.kms_breaker_cooldown == DEFAULT_KMS_BREAKER_COOLDOWN
    assert cfg.host == DEFAULT_HOST
    assert cfg.port == DEFAULT_PORT
    assert cfg.session_ttl_seconds == DEFAULT_SESSION_TTL_SECONDS


def test_config_custom_values() -> None:
    env = {
        "API_DATABASE_URL": "postgresql://user:pass@db:5432/custom",
        "API_TEST_ADMIN_URL": "postgresql://user:pass@db:5432/admin",
        "API_TEST_URL": "postgresql://user:pass@db:5432/test",
        "API_REDIS_URL": "redis://custom-redis:6379/2",
        "API_DEK_CACHE_TTL": "1200",
        "API_DEK_CACHE_L1_TTL": "30",
        "API_INFISICAL_URL": "http://kms.local:8080",
        "API_INFISICAL_TOKEN": "token-xyz",
        "API_INFISICAL_KMS_KEY_ID": VALID_UUID,
        "API_KMS_BREAKER_THRESHOLD": "5",
        "API_KMS_BREAKER_COOLDOWN": "45.5",
        "HOST": "127.0.0.1",
        "PORT": "9000",
        "API_SESSION_TTL_SECONDS": "3600",
    }
    cfg = Config.from_env(env)
    assert cfg.database_url == "postgresql://user:pass@db:5432/custom"
    assert cfg.test_admin_url == "postgresql://user:pass@db:5432/admin"
    assert cfg.test_database_url == "postgresql://user:pass@db:5432/test"
    assert cfg.redis_url == "redis://custom-redis:6379/2"
    assert cfg.dek_cache_ttl == 1200
    assert cfg.dek_cache_l1_ttl == 30
    assert cfg.infisical_url == "http://kms.local:8080"
    assert cfg.infisical_token == "token-xyz"
    assert cfg.infisical_kms_key_id == VALID_UUID
    assert cfg.kms_breaker_threshold == 5
    assert cfg.kms_breaker_cooldown == pytest.approx(45.5, abs=1e-3)
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 9000
    assert cfg.session_ttl_seconds == 3600


@pytest.mark.parametrize(
    ("key", "val", "match"),
    [
        ("API_INFISICAL_KMS_KEY_ID", "not-a-uuid", "API_INFISICAL_KMS_KEY_ID must be a UUID"),
        ("API_KMS_BREAKER_THRESHOLD", "abc", "must be an integer"),
        ("API_KMS_BREAKER_THRESHOLD", "0", "must be at least 1"),
        ("API_KMS_BREAKER_COOLDOWN", "zero", "must be a number"),
        ("API_KMS_BREAKER_COOLDOWN", "0", "must be positive"),
        ("API_KMS_BREAKER_COOLDOWN", "-5.0", "must be positive"),
        ("API_DEK_CACHE_TTL", "bad", "must be an integer"),
        ("API_DEK_CACHE_TTL", "0", "must be at least 1 second"),
        ("API_DEK_CACHE_L1_TTL", "0", "must be at least 1 second"),
        ("PORT", "abc", "must be an integer"),
        ("PORT", "0", "must be between 1 and 65535"),
        ("PORT", "70000", "must be between 1 and 65535"),
        ("API_SESSION_TTL_SECONDS", "0", "must be at least 1 second"),
    ],
)
def test_config_fails_loud_on_invalid_env(key: str, val: str, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        Config.from_env({key: val})


def test_get_config_reads_os_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PORT", "8888")
    cfg = get_config()
    assert cfg.port == 8888
