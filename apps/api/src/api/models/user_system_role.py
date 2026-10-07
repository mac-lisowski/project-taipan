from enum import Enum

from sqlalchemy import CheckConstraint, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base
from api.models.user_role import allowed_roles_sql


class SystemRole(str, Enum):
    """Platform-level roles, independent of any tenant. Widening needs a migration."""

    SYSTEM_OWNER = "system_owner"


class UserSystemRole(Base):
    """Extension table: platform roles on a user, with no tenant column."""

    __tablename__ = "user_system_roles"
    __table_args__ = (
        CheckConstraint(allowed_roles_sql(SystemRole), name="ck_user_system_roles_role_allowed"),
        UniqueConstraint("user_id", "role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    role: Mapped[str] = mapped_column(Text)
