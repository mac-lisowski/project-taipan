"""Configuration module for the api application.

Loads environment variables in one place and validates them eagerly.
Fields group by concern so callers read `cfg.db.database_url`, not a
flat bag of fourteen names.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from crypto.envelope import is_valid_key_id

DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/app"
DEFAULT_REDIS_URL = "redis://localhost:6379/0"
DEFAULT_DEK_CACHE_TTL = 900
DEFAULT_DEK_CACHE_L1_TTL = 60
DEFAULT_INFISICAL_URL = "http://localhost:8080"
DEFAULT_KMS_BREAKER_THRESHOLD = 3
DEFAULT_KMS_BREAKER_COOLDOWN = 30.0
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000
DEFAULT_SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
DEFAULT_RESET_TOKEN_TTL_SECONDS = 3600
DEFAULT_MAIL_FROM = "noreply@localhost"
# Non-empty so a built reset link always passes render validation.
DEFAULT_APP_BASE_URL = "http://localhost:3000"


@dataclass(frozen=True)
class DbConfig:
    database_url: str = DEFAULT_DATABASE_URL


@dataclass(frozen=True)
class StoreConfig:
    redis_url: str = DEFAULT_REDIS_URL
    session_ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS
    reset_token_ttl_seconds: int = DEFAULT_RESET_TOKEN_TTL_SECONDS


@dataclass(frozen=True)
class CryptoConfig:
    infisical_url: str = DEFAULT_INFISICAL_URL
    infisical_token: str = ""
    infisical_kms_key_id: str = ""
    kms_breaker_threshold: int = DEFAULT_KMS_BREAKER_THRESHOLD
    kms_breaker_cooldown: float = DEFAULT_KMS_BREAKER_COOLDOWN
    dek_cache_ttl: int = DEFAULT_DEK_CACHE_TTL
    dek_cache_l1_ttl: int = DEFAULT_DEK_CACHE_L1_TTL


@dataclass(frozen=True)
class MailConfig:
    resend_api_key: str = ""
    mail_from_address: str = DEFAULT_MAIL_FROM
    resend_webhook_secret: str = ""
    app_base_url: str = DEFAULT_APP_BASE_URL


@dataclass(frozen=True)
class ServerConfig:
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT


@dataclass(frozen=True)
class Config:
    db: DbConfig
    store: StoreConfig
    crypto: CryptoConfig
    mail: MailConfig
    server: ServerConfig

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Config:
        e = os.environ if env is None else env

        token = e.get("API_INFISICAL_TOKEN", "")
        key_id = e.get("API_INFISICAL_KMS_KEY_ID", "")
        if key_id and not is_valid_key_id(key_id):
            raise ValueError("API_INFISICAL_KMS_KEY_ID must be a UUID")

        # Parses run in the pre-grouping order so invalid env fails the
        # same error first; the mail cross-check stays last.
        infisical_url = e.get("API_INFISICAL_URL", DEFAULT_INFISICAL_URL)
        threshold = _parse_int(
            e,
            "API_KMS_BREAKER_THRESHOLD",
            DEFAULT_KMS_BREAKER_THRESHOLD,
            lo=1,
            range_msg="API_KMS_BREAKER_THRESHOLD must be at least 1",
        )
        cooldown = _parse_float(e, "API_KMS_BREAKER_COOLDOWN", DEFAULT_KMS_BREAKER_COOLDOWN)
        dek_ttl = _parse_int(
            e,
            "API_DEK_CACHE_TTL",
            DEFAULT_DEK_CACHE_TTL,
            lo=1,
            range_msg="API_DEK_CACHE_TTL must be at least 1 second",
        )
        dek_l1_ttl = _parse_int(
            e,
            "API_DEK_CACHE_L1_TTL",
            DEFAULT_DEK_CACHE_L1_TTL,
            lo=1,
            range_msg="API_DEK_CACHE_L1_TTL must be at least 1 second",
        )
        host = e.get("HOST", DEFAULT_HOST)
        port = _parse_int(
            e,
            "PORT",
            DEFAULT_PORT,
            lo=1,
            hi=65535,
            range_msg="PORT must be between 1 and 65535",
        )
        session_ttl = _parse_int(
            e,
            "API_SESSION_TTL_SECONDS",
            DEFAULT_SESSION_TTL_SECONDS,
            lo=1,
            range_msg="API_SESSION_TTL_SECONDS must be at least 1 second",
        )
        reset_token_ttl = _parse_int(
            e,
            "API_RESET_TOKEN_TTL_SECONDS",
            DEFAULT_RESET_TOKEN_TTL_SECONDS,
            lo=1,
            range_msg="API_RESET_TOKEN_TTL_SECONDS must be at least 1 second",
        )

        resend_api_key = e.get("API_RESEND_API_KEY", "")
        mail_from = e.get("API_MAIL_FROM", DEFAULT_MAIL_FROM)
        resend_webhook_secret = e.get("API_RESEND_WEBHOOK_SECRET", "")
        if resend_api_key and not mail_from.strip():
            raise ValueError("API_MAIL_FROM must be non-empty when API_RESEND_API_KEY is set")

        return cls(
            db=DbConfig(database_url=e.get("API_DATABASE_URL", DEFAULT_DATABASE_URL)),
            store=StoreConfig(
                redis_url=e.get("API_REDIS_URL", DEFAULT_REDIS_URL),
                session_ttl_seconds=session_ttl,
                reset_token_ttl_seconds=reset_token_ttl,
            ),
            crypto=CryptoConfig(
                infisical_url=infisical_url,
                infisical_token=token,
                infisical_kms_key_id=key_id,
                kms_breaker_threshold=threshold,
                kms_breaker_cooldown=cooldown,
                dek_cache_ttl=dek_ttl,
                dek_cache_l1_ttl=dek_l1_ttl,
            ),
            mail=MailConfig(
                resend_api_key=resend_api_key,
                mail_from_address=mail_from,
                resend_webhook_secret=resend_webhook_secret,
                # An empty var would build a relative link the renderer rejects.
                app_base_url=e.get("API_APP_BASE_URL") or DEFAULT_APP_BASE_URL,
            ),
            server=ServerConfig(host=host, port=port),
        )


def _parse_int(
    e: Mapping[str, str],
    var: str,
    default: int,
    *,
    lo: int,
    range_msg: str,
    hi: int | None = None,
) -> int:
    """Parse one bounded int env var; bad text or range fails loud."""
    try:
        value = int(e.get(var, str(default)))
    except ValueError as err:
        raise ValueError(f"{var} must be an integer") from err
    if value < lo or (hi is not None and value > hi):
        raise ValueError(range_msg)
    return value


def _parse_float(e: Mapping[str, str], var: str, default: float) -> float:
    """Parse one positive float env var; bad text or sign fails loud."""
    try:
        value = float(e.get(var, str(default)))
    except ValueError as err:
        raise ValueError(f"{var} must be a number") from err
    if value <= 0:
        raise ValueError(f"{var} must be positive")
    return value


def get_config() -> Config:
    """Return application config loaded from current environment."""
    return Config.from_env()
