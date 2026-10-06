from enum import Enum

from sqlalchemy import CheckConstraint, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base


class Role(str, Enum):
    """Every role the system grants. Widening this set needs a migration."""

    ADMIN = "admin"
    MEMBER = "member"


def _allowed_roles_sql() -> str:
    values = ", ".join(sorted(repr(role.value) for role in Role))
    return f"role IN ({values})"


class UserRole(Base):
    """Extension table: roles attached to a user, never on users."""

    __tablename__ = "user_roles"
    __table_args__ = (
        CheckConstraint(_allowed_roles_sql(), name="ck_user_roles_role_allowed"),
        UniqueConstraint("user_id", "role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    role: Mapped[str] = mapped_column(Text)
