"""System settings acts: typed accessors over the key value table. No tenant scope, no FastAPI."""

from __future__ import annotations

from sqlalchemy.orm import Session

from api.models.system_setting import SystemSetting

__all__ = ["get_registration_enabled", "set_registration_enabled"]

_REGISTRATION_ENABLED = "registration_enabled"


def _get(db: Session, key: str) -> str | None:
    row = db.get(SystemSetting, key)
    return row.value if row is not None else None


def _set(db: Session, key: str, value: str) -> None:
    """Upsert one row; the request transaction commits in get_db."""
    row = db.get(SystemSetting, key)
    if row is None:
        db.add(SystemSetting(key=key, value=value))
    else:
        row.value = value
    db.flush()


def get_registration_enabled(db: Session) -> bool:
    # Missing key reads false: the platform starts with sign up closed.
    return _get(db, _REGISTRATION_ENABLED) == "true"


def set_registration_enabled(db: Session, enabled: bool) -> None:
    _set(db, _REGISTRATION_ENABLED, "true" if enabled else "false")
