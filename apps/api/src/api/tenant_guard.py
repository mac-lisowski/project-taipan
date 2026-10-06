"""Flush guard: tenant-carrying rows must agree with the ambient scope."""

from crypto import current_tenant
from crypto.errors import CryptoCategory, CryptoError
from sqlalchemy import event
from sqlalchemy.orm import Session

_UNSET = object()


def install() -> None:
    event.listen(Session, "before_flush", _check_tenant_rows)


def _check_tenant_rows(session: Session, _flush_context: object, _instances: object) -> None:
    ambient = current_tenant()
    for obj in list(session.new) + list(session.dirty):
        # __dict__ reads only what is loaded; no lazy load inside a flush.
        tenant_id = obj.__dict__.get("tenant_id", _UNSET)
        if tenant_id is _UNSET or tenant_id == ambient:
            continue
        raise CryptoError(
            CryptoCategory.MISSING_TENANT_SCOPE,
            "row tenant_id does not match the ambient scope",
        )
