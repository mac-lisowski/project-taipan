from sqlalchemy import select
from sqlalchemy.orm import Session

from api.db import Base


class BaseRepository[T: Base]:
    """Shared CRUD. Subclass and set `model` to get a repository for that table."""

    model: type[T]

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, obj_id: int) -> T | None:
        return self._session.get(self.model, obj_id)

    def list(self) -> list[T]:
        return list(self._session.scalars(select(self.model)))

    def add(self, obj: T) -> T:
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return obj

    def delete(self, obj: T) -> None:
        self._session.delete(obj)
        self._session.commit()
