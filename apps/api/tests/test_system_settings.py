"""System settings module tests: real session, no HTTP. Router wiring is pinned in test_settings_api.py."""

from api import system_settings
from api.models import SystemSetting
from sqlalchemy import func, select


def test_missing_key_reads_false(session_factory):
    with session_factory() as db:
        assert system_settings.get_registration_enabled(db) is False


def test_set_then_get_round_trips_both_values(session_factory):
    with session_factory() as db:
        system_settings.set_registration_enabled(db, True)
        assert system_settings.get_registration_enabled(db) is True

        system_settings.set_registration_enabled(db, False)
        assert system_settings.get_registration_enabled(db) is False


def test_set_on_existing_key_upserts_single_row(session_factory):
    with session_factory() as db:
        system_settings.set(db, system_settings.REGISTRATION_ENABLED, "true")
        system_settings.set(db, system_settings.REGISTRATION_ENABLED, "false")

        row_count = db.scalar(
            select(func.count())
            .select_from(SystemSetting)
            .where(SystemSetting.key == system_settings.REGISTRATION_ENABLED)
        )
        assert row_count == 1
        assert system_settings.get(db, system_settings.REGISTRATION_ENABLED) == "false"


def test_get_returns_none_for_unknown_key(session_factory):
    with session_factory() as db:
        assert system_settings.get(db, "no-such-key") is None
