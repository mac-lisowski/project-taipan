from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db import Base

if TYPE_CHECKING:
    from api.models.user import User


class UserProfile(Base):
    """Pattern A extension table: profile data lives here, never on users."""

    __tablename__ = "user_profiles"
    __table_args__ = (
        # The API caps these fields too; the CHECKs bound what bypasses it.
        CheckConstraint("LENGTH(display_name) <= 100", name="ck_user_profiles_display_name_len"),
        CheckConstraint("LENGTH(avatar_url) <= 2048", name="ck_user_profiles_avatar_url_len"),
        CheckConstraint("LENGTH(bio) <= 5000", name="ck_user_profiles_bio_len"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    display_name: Mapped[str | None]
    avatar_url: Mapped[str | None]
    bio: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="profile")
