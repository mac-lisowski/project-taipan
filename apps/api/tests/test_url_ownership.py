"""Pins for ticket 01: test urls leave production config.

Production Config knows nothing about test databases. The test suite
owns its urls in api_testsupport, read from API_TEST_* env at import
with frozen localhost defaults.
"""

import importlib

import api_testsupport
import pytest
from api.config import Config
from sqlalchemy.engine import make_url


def test_config_has_no_test_url_fields() -> None:
    cfg = Config.from_env({})
    assert not hasattr(cfg, "test_admin_url")
    assert not hasattr(cfg, "test_database_url")


def test_config_module_has_no_test_url_constants() -> None:
    import api.config

    assert not any(name.startswith("DEFAULT_TEST") for name in vars(api.config))


def test_testsupport_urls_default_to_localhost(monkeypatch: pytest.MonkeyPatch) -> None:
    """Defaults bind at import, so clear the env and reload to observe them."""
    monkeypatch.delenv("API_TEST_ADMIN_URL", raising=False)
    monkeypatch.delenv("API_TEST_URL", raising=False)
    # Reload mutates the shared module; put the import-time values back.
    saved = (api_testsupport.TEST_ADMIN_URL, api_testsupport.TEST_URL)
    try:
        support = importlib.reload(api_testsupport)
    finally:
        api_testsupport.TEST_ADMIN_URL, api_testsupport.TEST_URL = saved
    admin = make_url(support.TEST_ADMIN_URL)
    test = make_url(support.TEST_URL)
    assert (admin.drivername, admin.host, admin.port, admin.database) == (
        "postgresql+psycopg",
        "localhost",
        5432,
        "postgres",
    )
    assert (test.drivername, test.host, test.port, test.database) == (
        "postgresql+psycopg",
        "localhost",
        5432,
        "app_test",
    )
