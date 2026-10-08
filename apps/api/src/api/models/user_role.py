from enum import Enum


class Role(str, Enum):
    """Tenant roles the system grants. Widening this set needs a migration."""

    ADMIN = "admin"
    MEMBER = "member"


def allowed_roles_sql(enum: type[Enum]) -> str:
    values = ", ".join(sorted(repr(role.value) for role in enum))
    return f"role IN ({values})"
