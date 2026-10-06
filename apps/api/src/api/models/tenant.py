from datetime import datetime

from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base


class Tenant(Base):
    """One personal tenant per user; encrypted rows scope to its id."""

    __tablename__ = "tenants"

    # App-generated uuid4 hex; the crypto seam carries tenant ids as str.
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
