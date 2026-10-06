"""Configuration module for the api application.

Loads environment variables in one place and validates them eagerly.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from crypto.envelope import is_valid_key_id

DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/app"
DEFAULT_TEST_ADMIN_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
DEFAULT_TEST_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/app_test"
DEFAULT_REDIS_URL = "redis://localhost:6379/0"
DEFAULT_DEK_CACHE_TTL = 900
DEFAULT_DEK_CACHE_L1_TTL = 60
DEFAULT_INFISICAL_URL = "http://localhost:8080"
DEFAULT_KMS_BREAKER_THRESHOLD = 3
DEFAULT_KMS_BREAKER_COOLDOWN = 30.0
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000
DEFAULT_SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
DEFAULT_MAIL_FROM = "noreply@localhost"


@dataclass(frozen=True)
class Config:
    database_url: str = DEFAULT_DATABASE_URL
    test_admin_url: str = DEFAULT_TEST_ADMIN_URL
    test_database_url: str = DEFAULT_TEST_URL
    redis_url: str = DEFAULT_REDIS_URL
    dek_cache_ttl: int = DEFAULT_DEK_CACHE_TTL
    dek_cache_l1_ttl: int = DEFAULT_DEK_CACHE_L1_TTL
    infisical_url: str = DEFAULT_INFISICAL_URL
    infisical_token: str = ""
    infisical_kms_key_id: str = ""
    kms_breaker_threshold: int = DEFAULT_KMS_BREAKER_THRESHOLD
    kms_breaker_cooldown: float = DEFAULT_KMS_BREAKER_COOLDOWN
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    session_ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS
    resend_api_key: str = ""
    mail_from_address: str = DEFAULT_MAIL_FROM

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Config:
        e = os.environ if env is None else env

        database_url = e.get("API_DATABASE_URL", DEFAULT_DATABASE_URL)
        test_admin_url = e.get("API_TEST_ADMIN_URL", DEFAULT_TEST_ADMIN_URL)
        test_database_url = e.get("API_TEST_URL", DEFAULT_TEST_URL)
        redis_url = e.get("API_REDIS_URL", DEFAULT_REDIS_URL)

        token = e.get("API_INFISICAL_TOKEN", "")
        key_id = e.get("API_INFISICAL_KMS_KEY_ID", "")
        if key_id and not is_valid_key_id(key_id):
            raise ValueError("API_INFISICAL_KMS_KEY_ID must be a UUID")

        infisical_url = e.get("API_INFISICAL_URL", DEFAULT_INFISICAL_URL)

        try:
            breaker_threshold = int(
                e.get("API_KMS_BREAKER_THRESHOLD", str(DEFAULT_KMS_BREAKER_THRESHOLD))
            )
        except ValueError as err:
            raise ValueError("API_KMS_BREAKER_THRESHOLD must be an integer") from err
        if breaker_threshold < 1:
            raise ValueError("API_KMS_BREAKER_THRESHOLD must be at least 1")

        try:
            breaker_cooldown = float(
                e.get("API_KMS_BREAKER_COOLDOWN", str(DEFAULT_KMS_BREAKER_COOLDOWN))
            )
        except ValueError as err:
            raise ValueError("API_KMS_BREAKER_COOLDOWN must be a number") from err
        if breaker_cooldown <= 0:
            raise ValueError("API_KMS_BREAKER_COOLDOWN must be positive")

        try:
            dek_ttl = int(e.get("API_DEK_CACHE_TTL", str(DEFAULT_DEK_CACHE_TTL)))
        except ValueError as err:
            raise ValueError("API_DEK_CACHE_TTL must be an integer") from err
        if dek_ttl < 1:
            raise ValueError("API_DEK_CACHE_TTL must be at least 1 second")

        try:
            dek_l1_ttl = int(e.get("API_DEK_CACHE_L1_TTL", str(DEFAULT_DEK_CACHE_L1_TTL)))
        except ValueError as err:
            raise ValueError("API_DEK_CACHE_L1_TTL must be an integer") from err
        if dek_l1_ttl < 1:
            raise ValueError("API_DEK_CACHE_L1_TTL must be at least 1 second")

        host = e.get("HOST", DEFAULT_HOST)

        try:
            port = int(e.get("PORT", str(DEFAULT_PORT)))
        except ValueError as err:
            raise ValueError("PORT must be an integer") from err
        if not (1 <= port <= 65535):
            raise ValueError("PORT must be between 1 and 65535")

        try:
            session_ttl = int(e.get("API_SESSION_TTL_SECONDS", str(DEFAULT_SESSION_TTL_SECONDS)))
        except ValueError as err:
            raise ValueError("API_SESSION_TTL_SECONDS must be an integer") from err
        if session_ttl < 1:
            raise ValueError("API_SESSION_TTL_SECONDS must be at least 1 second")

        resend_api_key = e.get("API_RESEND_API_KEY", "")
        mail_from = e.get("API_MAIL_FROM", DEFAULT_MAIL_FROM)
        if resend_api_key and not mail_from.strip():
            raise ValueError("API_MAIL_FROM must be non-empty when API_RESEND_API_KEY is set")

        return cls(
            database_url=database_url,
            test_admin_url=test_admin_url,
            test_database_url=test_database_url,
            redis_url=redis_url,
            dek_cache_ttl=dek_ttl,
            dek_cache_l1_ttl=dek_l1_ttl,
            infisical_url=infisical_url,
            infisical_token=token,
            infisical_kms_key_id=key_id,
            kms_breaker_threshold=breaker_threshold,
            kms_breaker_cooldown=breaker_cooldown,
            host=host,
            port=port,
            session_ttl_seconds=session_ttl,
            resend_api_key=resend_api_key,
            mail_from_address=mail_from,
        )


def get_config() -> Config:
    """Return application config loaded from current environment."""
    return Config.from_env()
