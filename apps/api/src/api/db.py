from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from api import tenant_guard
from api.config import get_config

DATABASE_URL = get_config().db.database_url

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

# The guard is session-global: every flush checks tenant-carrying rows.
tenant_guard.install()


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    """The request owns the transaction: commit on success, roll back on any error."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


DbSession = Annotated[Session, Depends(get_db)]
