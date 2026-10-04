import sys
from pathlib import Path

from alembic.config import main as alembic_main

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def _run(*args: str) -> None:
    alembic_main(argv=["-c", str(ALEMBIC_INI), *args])


def revision() -> None:
    _run("revision", "--autogenerate", *sys.argv[1:])


def upgrade() -> None:
    _run("upgrade", "head")


def downgrade() -> None:
    _run("downgrade", "-1")


def current() -> None:
    _run("current")


def stamp() -> None:
    _run("stamp", *sys.argv[1:])
