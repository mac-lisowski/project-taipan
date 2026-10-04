from core import greet


def test_greet() -> None:
    assert greet("monorepo") == "Hello, monorepo!"
