"""System settings acts: global key value get and upsert. No tenant scope, no FastAPI."""

from __future__ import annotations

from sqlalchemy.orm import Session

from api.models.system_setting import SystemSetting

__all__ = [
    "REGISTRATION_ENABLED",
    "get",
    "get_registration_enabled",
    "set",
    "set_registration_enabled",
]

REGISTRATION_ENABLED = "registration_enabled"


def get(db: Session, key: str) -> str | None:
    row = db.get(SystemSetting, key)
    return row.value if row is not None else None


def set(db: Session, key: str, value: str) -> None:
    """Upsert one row; the request transaction commits in get_db."""
    row = db.get(SystemSetting, key)
    if row is None:
        db.add(SystemSetting(key=key, value=value))
    else:
        row.value = value
    db.flush()


def get_registration_enabled(db: Session) -> bool:
    # Missing key reads false: the platform starts with sign up closed.
    return get(db, REGISTRATION_ENABLED) == "true"


def set_registration_enabled(db: Session, enabled: bool) -> None:
    set(db, REGISTRATION_ENABLED, "true" if enabled else "false")
