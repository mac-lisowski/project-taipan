from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base


class TenantDek(Base):
    """One wrapped per-tenant data key; the tenant owns at most one."""

    __tablename__ = "tenant_deks"
    __table_args__ = (
        # The envelope grammar already validates on decrypt; these bound
        # what corruption can store so the table fails loud at insert.
        CheckConstraint("LENGTH(key_id) <= 64", name="ck_tenant_deks_key_id_len"),
        CheckConstraint(
            "LENGTH(wrapped_dek) BETWEEN 20 AND 512",
            name="ck_tenant_deks_wrapped_dek_len",
        ),
    )

    tenant_id: Mapped[str] = mapped_column(Text, primary_key=True)
    key_id: Mapped[str] = mapped_column(Text)
    wrapped_dek: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
