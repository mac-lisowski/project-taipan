"""Tests for the messaging (NATS JetStream) config group."""

import pytest
from api.config import (
    DEFAULT_BROKER_URL,
    DEFAULT_JETSTREAM_STORE,
    Config,
)


def test_broker_url_default_is_local_nats() -> None:
    assert DEFAULT_BROKER_URL == "nats://localhost:4222"
    assert Config.from_env({}).msg.broker_url == DEFAULT_BROKER_URL


def test_jetstream_store_default_is_file() -> None:
    assert DEFAULT_JETSTREAM_STORE == "file"
    assert Config.from_env({}).msg.jetstream_store == DEFAULT_JETSTREAM_STORE


def test_jetstream_store_env_selects_memory() -> None:
    cfg = Config.from_env({"API_JETSTREAM_STORE": "memory"})

    assert cfg.msg.jetstream_store == "memory"


@pytest.mark.parametrize("val", ["disk", "MEMORY", "ram", ""])
def test_jetstream_store_fails_loud_on_bad_values(val: str) -> None:
    with pytest.raises(ValueError, match="API_JETSTREAM_STORE must be 'file' or 'memory'"):
        Config.from_env({"API_JETSTREAM_STORE": val})


def test_broker_url_env_strips_surrounding_whitespace() -> None:
    cfg = Config.from_env({"API_BROKER_URL": "  nats://edge:4222  "})

    assert cfg.msg.broker_url == "nats://edge:4222"
