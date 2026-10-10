"""Live contract: domain streams, replay, retention on a real broker.

Skip when the broker is unreachable, same convention as the other live
tests. What only a live run proves: a twice declaration is one stream,
retention lands on the stream config, the ordered consumer replays all
retained events oldest first, and a core-subject publish never enters
the stream. The domain is unique per run and the stream is torn down,
so runs leave no server state behind.
"""

import uuid
from typing import Any

import pytest
from messaging import MessagingError, define_stream, subject
from nats.js.api import RetentionPolicy

WAIT = 5.0


class Live:
    """Per-run domain namespace on the shared inspector link."""

    def __init__(self, inspector: Any) -> None:
        self.js = inspector.js
        self.streams = inspector.streams
        # A dotted domain: it also proves the fold into one stream token.
        self.domain = f"orders.{uuid.uuid4().hex[:12]}"

    @property
    def paid(self) -> str:
        return subject(self.domain, "order", "v1")

    def track(self, name: str) -> str:
        # Registered names are torn down by the shared inspector fixture.
        self.streams.append(name)
        return name


async def define(ctx: Live, broker: Any, retention: str = "limits") -> str:
    name = await define_stream(broker, ctx.domain, [ctx.paid], retention)
    return ctx.track(name)


@pytest.fixture
async def live_ctx(inspector: Any) -> Any:
    return Live(inspector)


@pytest.mark.anyio
async def test_declaring_a_stream_twice_is_idempotent(live_ctx: Live, broker_factory: Any) -> None:
    broker = broker_factory()
    name = await define(live_ctx, broker)
    again = await define(live_ctx, broker)

    info = await live_ctx.js.stream_info(name)
    await broker.drain()

    assert again == name
    assert list(info.config.subjects) == [live_ctx.paid]


@pytest.mark.anyio
async def test_replay_returns_all_retained_events_oldest_first(
    live_ctx: Live, broker_factory: Any
) -> None:
    broker = broker_factory()
    name = await define(live_ctx, broker)
    for n in (1, 2, 3):
        await broker.publish(live_ctx.paid, {"n": n})

    # A fresh link is the late reader: it replays what the first one stored.
    late = broker_factory()
    got = [dict(m.payload) async for m in late.replay(name, live_ctx.paid)]
    await broker.drain()
    await late.drain()

    assert got == [{"n": 1}, {"n": 2}, {"n": 3}]


@pytest.mark.anyio
async def test_core_publish_stays_outside_the_stream(live_ctx: Live, broker_factory: Any) -> None:
    broker = broker_factory()
    name = await define(live_ctx, broker)
    # A pricetick on an undeclared subject is a fast signal, not an event.
    await broker.publish(subject(live_ctx.domain, "pricetick", "v1"), {"n": 0})
    await broker.publish(live_ctx.paid, {"n": 1})

    # The wildcard filter takes every stream subject: only retained ones show.
    got = [dict(m.payload) async for m in broker.replay(name, ">")]
    await broker.drain()

    assert got == [{"n": 1}]


@pytest.mark.anyio
async def test_retention_defaults_to_limits_on_the_stream(
    live_ctx: Live, broker_factory: Any
) -> None:
    broker = broker_factory()
    name = await define(live_ctx, broker)

    info = await live_ctx.js.stream_info(name)
    await broker.drain()

    assert info.config.retention == RetentionPolicy.LIMITS


@pytest.mark.anyio
async def test_retention_override_lives_on_the_stream(live_ctx: Live, broker_factory: Any) -> None:
    broker = broker_factory()
    name = await define(live_ctx, broker, retention="workqueue")

    info = await live_ctx.js.stream_info(name)
    await broker.drain()

    assert info.config.retention == RetentionPolicy.WORK_QUEUE


@pytest.mark.anyio
async def test_replay_of_a_missing_stream_fails_loud(live_ctx: Live, broker_factory: Any) -> None:
    broker = broker_factory()

    with pytest.raises(MessagingError):
        async for _ in broker.replay(f"orders-{uuid.uuid4().hex[:12]}", ">"):
            pass
    await broker.drain()
