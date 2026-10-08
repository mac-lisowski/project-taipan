"""Tests for the grouped, frozen application configuration."""

from dataclasses import FrozenInstanceError, fields

import pytest
from api.config import (
    DEFAULT_DATABASE_URL,
    DEFAULT_DEK_CACHE_L1_TTL,
    DEFAULT_DEK_CACHE_TTL,
    DEFAULT_HOST,
    DEFAULT_INFISICAL_URL,
    DEFAULT_KMS_BREAKER_COOLDOWN,
    DEFAULT_KMS_BREAKER_THRESHOLD,
    DEFAULT_MAIL_FROM,
    DEFAULT_PORT,
    DEFAULT_REDIS_URL,
    DEFAULT_SESSION_TTL_SECONDS,
    Config,
    get_config,
)

VALID_UUID = "5f0c9a1e-2222-4333-8444-555566667777"


def test_config_holds_only_the_expected_groups() -> None:
    assert [f.name for f in fields(Config)] == [
        "db",
        "store",
        "crypto",
        "mail",
        "server",
        "chat",
    ]


def test_config_defaults() -> None:
    cfg = Config.from_env({})
    assert cfg.db.database_url == DEFAULT_DATABASE_URL
    assert cfg.store.redis_url == DEFAULT_REDIS_URL
    assert cfg.store.session_ttl_seconds == DEFAULT_SESSION_TTL_SECONDS
    assert cfg.crypto.infisical_url == DEFAULT_INFISICAL_URL
    assert cfg.crypto.infisical_token == ""
    assert cfg.crypto.infisical_kms_key_id == ""
    assert cfg.crypto.kms_breaker_threshold == DEFAULT_KMS_BREAKER_THRESHOLD
    assert cfg.crypto.kms_breaker_cooldown == DEFAULT_KMS_BREAKER_COOLDOWN
    assert cfg.crypto.dek_cache_ttl == DEFAULT_DEK_CACHE_TTL
    assert cfg.crypto.dek_cache_l1_ttl == DEFAULT_DEK_CACHE_L1_TTL
    assert cfg.mail.resend_api_key == ""
    assert cfg.mail.mail_from_address == DEFAULT_MAIL_FROM
    assert cfg.server.host == DEFAULT_HOST
    assert cfg.server.port == DEFAULT_PORT


def test_config_custom_values() -> None:
    env = {
        "API_DATABASE_URL": "postgresql://user:pass@db:5432/custom",
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
    assert cfg.db.database_url == "postgresql://user:pass@db:5432/custom"
    assert cfg.store.redis_url == "redis://custom-redis:6379/2"
    assert cfg.crypto.dek_cache_ttl == 1200
    assert cfg.crypto.dek_cache_l1_ttl == 30
    assert cfg.crypto.infisical_url == "http://kms.local:8080"
    assert cfg.crypto.infisical_token == "token-xyz"
    assert cfg.crypto.infisical_kms_key_id == VALID_UUID
    assert cfg.crypto.kms_breaker_threshold == 5
    assert cfg.crypto.kms_breaker_cooldown == pytest.approx(45.5, abs=1e-3)
    assert cfg.mail.resend_api_key == ""
    assert cfg.mail.mail_from_address == DEFAULT_MAIL_FROM
    assert cfg.server.host == "127.0.0.1"
    assert cfg.server.port == 9000
    assert cfg.store.session_ttl_seconds == 3600


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


@pytest.mark.parametrize(
    ("env", "match"),
    [
        (
            {"API_RESEND_API_KEY": "rk", "API_MAIL_FROM": "", "PORT": "abc"},
            "PORT must be an integer",
        ),
        (
            {"API_SESSION_TTL_SECONDS": "x", "PORT": "y"},
            "PORT must be an integer",
        ),
    ],
)
def test_multi_invalid_env_keeps_old_error_order(env: dict[str, str], match: str) -> None:
    # Numeric parses precede the mail cross-check; which error wins is contract.
    with pytest.raises(ValueError, match=match):
        Config.from_env(env)


def test_chat_config_defaults() -> None:
    # Literals, not constants: the dev defaults are the spec's pinned values.
    cfg = Config.from_env({})
    assert cfg.chat.litellm_url == "http://localhost:4000"
    assert cfg.chat.litellm_api_key == ""
    assert cfg.chat.chat_model == "gpt-4o-mini"


def test_chat_config_custom_values() -> None:
    env = {
        "API_LITELLM_URL": "http://litellm:4000/",
        "API_LITELLM_API_KEY": "sk-dev-key",
        "API_CHAT_MODEL": "llama-3",
    }
    cfg = Config.from_env(env)
    assert cfg.chat.litellm_url == "http://litellm:4000/"
    assert cfg.chat.litellm_api_key == "sk-dev-key"
    assert cfg.chat.chat_model == "llama-3"


def test_empty_chat_env_vars_fall_back_to_defaults() -> None:
    cfg = Config.from_env({"API_LITELLM_URL": "", "API_CHAT_MODEL": ""})
    assert cfg.chat.litellm_url == "http://localhost:4000"
    assert cfg.chat.chat_model == "gpt-4o-mini"


def test_same_env_yields_equal_config() -> None:
    env = {
        "API_DATABASE_URL": "postgresql://user:pass@db:5432/custom",
        "API_INFISICAL_TOKEN": "token-xyz",
        "PORT": "9000",
    }
    assert Config.from_env(env) == Config.from_env(env)


def test_config_has_no_test_url_fields() -> None:
    cfg = Config.from_env({})
    assert not any(f.name.startswith("test_") for f in fields(cfg))


@pytest.mark.parametrize(
    ("group", "field"),
    [
        ("db", "database_url"),
        ("store", "session_ttl_seconds"),
        ("crypto", "dek_cache_ttl"),
        ("mail", "mail_from_address"),
        ("server", "port"),
        ("chat", "chat_model"),
    ],
)
def test_groups_are_frozen(group: str, field: str) -> None:
    # Frozen-ness is class-wide; one field per group suffices, the
    # inventory is pinned by the five-groups and defaults tests.
    cfg = Config.from_env({})
    with pytest.raises(FrozenInstanceError):
        setattr(getattr(cfg, group), field, "x")
    with pytest.raises(FrozenInstanceError):
        setattr(cfg, group, None)


def test_get_config_reads_os_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PORT", "8888")
    cfg = get_config()
    assert cfg.server.port == 8888


def test_get_config_is_uncached(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PORT", "8888")
    first = get_config()
    monkeypatch.setenv("PORT", "9999")
    second = get_config()
    assert first.server.port == 8888
    assert second.server.port == 9999


@pytest.mark.parametrize(
    "reexport",
    [
        "DEFAULT_DEK_CACHE_TTL_SECONDS",
        "DEFAULT_DEK_L1_TTL_SECONDS",
        "DEFAULT_KMS_BREAKER_THRESHOLD",
        "DEFAULT_KMS_BREAKER_COOLDOWN_SECONDS",
    ],
)
def test_field_crypto_reexports_no_config_constants(reexport: str) -> None:
    # The composition root consumes config values; it is not a re-export surface.
    import api.field_crypto

    assert not hasattr(api.field_crypto, reexport)
