# Import every model module here. Base.metadata only sees tables
# whose module was imported; create_all silently skips the rest.
from api.models.auth_session import AuthSession
from api.models.dek import TenantDek
from api.models.email_suppression import (
    EmailSendCounter,
    EmailSuppression,
    EmailWebhookEvent,
)
from api.models.encrypted_string import EncryptedString
from api.models.profile import UserProfile
from api.models.system_setting import SystemSetting
from api.models.tenant import Tenant
from api.models.user import User
from api.models.user_role import Role
from api.models.user_system_role import SystemRole, UserSystemRole
from api.models.user_tenant import UserTenant
from api.models.user_tenant_role import UserTenantRole

__all__ = [
    "AuthSession",
    "EmailSendCounter",
    "EmailSuppression",
    "EmailWebhookEvent",
    "EncryptedString",
    "Role",
    "SystemRole",
    "SystemSetting",
    "Tenant",
    "TenantDek",
    "User",
    "UserProfile",
    "UserSystemRole",
    "UserTenant",
    "UserTenantRole",
]
