# Import every model module here. Base.metadata only sees tables
# whose module was imported; create_all silently skips the rest.
from api.models.user import User

__all__ = ["User"]
