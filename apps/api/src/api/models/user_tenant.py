from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db import Base

if TYPE_CHECKING:
    from api.models.user import User


class UserTenant(Base):
    """Pattern A extension table: the user-to-tenant link, never on users."""

    __tablename__ = "user_tenants"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    tenant_id: Mapped[str] = mapped_column(Text, ForeignKey("tenants.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="tenant_link")
