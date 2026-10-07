from sqlalchemy import CheckConstraint, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base
from api.models.user_role import Role, allowed_roles_sql


class UserTenantRole(Base):
    """Extension table: roles bound to one tenant, never on users."""

    __tablename__ = "user_tenant_roles"
    __table_args__ = (
        CheckConstraint(allowed_roles_sql(Role), name="ck_user_tenant_roles_role_allowed"),
        UniqueConstraint("user_id", "tenant_id", "role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    tenant_id: Mapped[str] = mapped_column(Text, ForeignKey("tenants.id"))
    role: Mapped[str] = mapped_column(Text)
