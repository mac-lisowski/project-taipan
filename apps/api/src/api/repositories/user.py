from sqlalchemy import select

from api.models import User
from api.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        return self._session.scalar(select(User).where(User.email == email))
