"""DekStore adapter over the api database: durable wrapped DEKs."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from api.models import TenantDek


class PostgresDekStore:
    """Implements the crypto DekStore port. Put adopts the stored row."""

    def __init__(self, session_factory: sessionmaker[Session], key_id: str) -> None:
        self._session_factory = session_factory
        # Provenance column: unwrap always uses the envelope's key id, not this.
        self._key_id = key_id

    def get(self, tenant_id: str) -> str | None:
        with self._session_factory() as session:
            row = session.get(TenantDek, tenant_id)
            return row.wrapped_dek if row else None

    def put(self, tenant_id: str, wrapped_dek: str) -> str:
        with self._session_factory() as session:
            session.add(
                TenantDek(tenant_id=tenant_id, key_id=self._key_id, wrapped_dek=wrapped_dek)
            )
            try:
                session.commit()
            except IntegrityError:
                # A racing put owns the row; read back and adopt its value.
                session.rollback()
            row = session.get(TenantDek, tenant_id)
            if row is None:
                # The winner vanished mid-race; a silent None would poison callers.
                raise RuntimeError("dek row disappeared during put")
            return row.wrapped_dek
