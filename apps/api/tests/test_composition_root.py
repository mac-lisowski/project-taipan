"""Composition-root startup checks. No Infisical, no database, no Redis."""

import pytest
from api.field_crypto import build_field_crypto
from crypto import FieldCrypto

VALID_KEY_ID = "5f0c9a1e-2222-4333-8444-555566667777"


def _pin_env(monkeypatch: pytest.MonkeyPatch, key_id: str) -> None:
    # Pin every var the builder reads so ambient env cannot flip the result.
    monkeypatch.setenv("API_INFISICAL_TOKEN", "test-token")
    monkeypatch.setenv("API_INFISICAL_KMS_KEY_ID", key_id)
    for var in (
        "API_INFISICAL_URL",
        "API_REDIS_URL",
        "API_DEK_CACHE_TTL",
        "API_DEK_CACHE_L1_TTL",
        "API_KMS_BREAKER_THRESHOLD",
        "API_KMS_BREAKER_COOLDOWN",
    ):
        monkeypatch.delenv(var, raising=False)


def test_build_rejects_malformed_key_id(monkeypatch: pytest.MonkeyPatch) -> None:
    # Braced and urn forms parse as UUIDs but the envelope grammar rejects
    # them, so they must fail here, not at the first encrypt.
    exotic = ("{" + VALID_KEY_ID + "}", "urn:uuid:" + VALID_KEY_ID)
    for key_id in ("kms-key-alias", "5f0c9a1e-2222-4333-8444", *exotic):
        _pin_env(monkeypatch, key_id)
        with pytest.raises(ValueError, match="API_INFISICAL_KMS_KEY_ID"):
            build_field_crypto()


def test_build_with_empty_key_id_leaves_module_off(monkeypatch: pytest.MonkeyPatch) -> None:
    _pin_env(monkeypatch, "")
    assert build_field_crypto() is None


def test_build_with_valid_uuid_key_id_builds(monkeypatch: pytest.MonkeyPatch) -> None:
    _pin_env(monkeypatch, VALID_KEY_ID)
    module = build_field_crypto()
    assert isinstance(module, FieldCrypto)


@pytest.mark.anyio
async def test_lifespan_runs_upgrade_when_auto_migrate_set(monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import MagicMock

    from api import db_cli
    from api.main import app, lifespan

    mock_upgrade = MagicMock()
    monkeypatch.setattr(db_cli, "upgrade", mock_upgrade)
    monkeypatch.setenv("API_AUTO_MIGRATE", "1")
    async with lifespan(app):
        pass
    mock_upgrade.assert_called_once()


@pytest.mark.anyio
async def test_lifespan_skips_upgrade_when_auto_migrate_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from unittest.mock import MagicMock

    from api import db_cli
    from api.main import app, lifespan

    mock_upgrade = MagicMock()
    monkeypatch.setattr(db_cli, "upgrade", mock_upgrade)
    monkeypatch.delenv("API_AUTO_MIGRATE", raising=False)
    async with lifespan(app):
        pass
    mock_upgrade.assert_not_called()


def test_wait_for_db_raises_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    from api.db_cli import wait_for_db
    from sqlalchemy.exc import OperationalError

    monkeypatch.setenv(
        "API_DATABASE_URL", "postgresql+psycopg://postgres:postgres@127.0.0.1:59999/app"
    )
    with pytest.raises(OperationalError):
        wait_for_db(timeout_seconds=0.1, interval=0.05)
