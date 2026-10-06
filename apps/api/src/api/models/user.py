from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db import Base

if TYPE_CHECKING:
    from api.models.profile import UserProfile
    from api.models.user_tenant import UserTenant


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[str]
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Core identity stays here; profile data belongs to the
    # user_profiles extension table. ORM cascade mirrors the DB cascade.
    profile: Mapped["UserProfile | None"] = relationship(
        "UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    tenant_link: Mapped["UserTenant | None"] = relationship(
        "UserTenant", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
