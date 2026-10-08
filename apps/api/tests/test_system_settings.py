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
    key = "registration_enabled"
    with session_factory() as db:
        system_settings.set_registration_enabled(db, True)
        system_settings.set_registration_enabled(db, False)

        row_count = db.scalar(
            select(func.count()).select_from(SystemSetting).where(SystemSetting.key == key)
        )
        assert row_count == 1
        stored_value = db.scalar(select(SystemSetting.value).where(SystemSetting.key == key))
        assert stored_value == "false"


def test_public_surface_is_typed_pair_only():
    assert sorted(system_settings.__all__) == [
        "get_registration_enabled",
        "set_registration_enabled",
    ]
    for raw_name in ("get", "set", "REGISTRATION_ENABLED"):
        assert not hasattr(system_settings, raw_name)
