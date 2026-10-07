"""NatsBroker unit tier: lazy connect contract. No broker needed."""

import socket

import pytest
from messaging import MessagingError
from messaging.nats import NatsBroker

pytestmark = pytest.mark.anyio


def _closed_port_url() -> str:
    # A just-freed port refuses connects at once, whatever the env runs.
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return f"nats://127.0.0.1:{probe.getsockname()[1]}"


UNREACHABLE = _closed_port_url()
SHORT = 0.2


async def test_build_does_not_connect() -> None:
    broker = NatsBroker(UNREACHABLE, connect_timeout=SHORT)

    assert broker.connected is False


async def test_use_before_broker_raises_a_seam_error() -> None:
    broker = NatsBroker(UNREACHABLE, connect_timeout=SHORT)

    with pytest.raises(MessagingError):
        await broker.publish("events.test", {"ok": True})


async def test_subscribe_before_broker_raises_a_seam_error() -> None:
    broker = NatsBroker(UNREACHABLE, connect_timeout=SHORT)

    async def handler(msg: object) -> None:
        return None

    with pytest.raises(MessagingError):
        await broker.subscribe("events.test", handler)


async def test_connected_stays_false_after_a_failed_use() -> None:
    broker = NatsBroker(UNREACHABLE, connect_timeout=SHORT)
    with pytest.raises(MessagingError):
        await broker.publish("events.test", {"ok": True})

    assert broker.connected is False


async def test_drain_without_a_broker_is_a_noop() -> None:
    broker = NatsBroker(UNREACHABLE, connect_timeout=SHORT)

    await broker.drain()

    assert broker.connected is False


async def test_use_after_drain_raises_without_touching_the_network() -> None:
    broker = NatsBroker(UNREACHABLE, connect_timeout=SHORT)
    await broker.drain()

    with pytest.raises(MessagingError):
        await broker.publish("events.test", {"ok": True})


async def test_bad_retention_fails_loud_before_the_network() -> None:
    broker = NatsBroker(UNREACHABLE, connect_timeout=SHORT)

    with pytest.raises(ValueError):
        await broker.ensure_stream("s", ["a.b.c"], retention="bogus")
