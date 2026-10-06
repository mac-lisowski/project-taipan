import sys
import time
from pathlib import Path

from alembic.config import main as alembic_main
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from api.config import get_config

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def wait_for_db(timeout_seconds: float = 10.0, interval: float = 1.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    url = get_config().database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    eng = create_engine(url, connect_args=connect_args)
    try:
        while True:
            try:
                with eng.connect() as conn:
                    conn.execute(text("SELECT 1"))
                return
            except OperationalError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(interval)
    finally:
        eng.dispose()


def _run(*args: str) -> None:
    alembic_main(argv=["-c", str(ALEMBIC_INI), *args])


def revision() -> None:
    _run("revision", "--autogenerate", *sys.argv[1:])


def upgrade() -> None:
    wait_for_db()
    _run("upgrade", "head")


def downgrade() -> None:
    _run("downgrade", "-1")


def current() -> None:
    _run("current")


def stamp() -> None:
    _run("stamp", *sys.argv[1:])
