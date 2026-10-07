"""FakeBroker domain streams: define_stream and replay. No broker.

The fake pins the stream contract brokerless: one stream per domain,
idempotent declaration, retention from the declaration onward, and a
late reader that replays retained events oldest first.
"""

import pytest
from messaging import FakeBroker, MessagingError, define_stream, subject

pytestmark = pytest.mark.anyio

PAID = subject("orders", "order", "v1")
REFUNDED = subject("orders", "refund", "v1")


async def test_define_stream_names_the_stream_after_the_domain() -> None:
    broker = FakeBroker()

    name = await define_stream(broker, "orders", [PAID])

    assert name == "orders"


async def test_a_dotted_domain_folds_into_one_stream_token() -> None:
    broker = FakeBroker()

    name = await define_stream(broker, "jobs.a1b2", [subject("jobs.a1b2", "mail", "v1")])

    # A stream name is one token: dots have nowhere to go but a dash.
    assert name == "jobs-a1b2"


async def test_replay_returns_captured_events_to_a_late_reader_in_order() -> None:
    broker = FakeBroker()
    name = await define_stream(broker, "orders", [PAID])
    for n in (1, 2, 3):
        await broker.publish(PAID, {"n": n})

    got = [dict(m.payload) async for m in broker.replay(name, PAID)]

    assert got == [{"n": 1}, {"n": 2}, {"n": 3}]


async def test_replay_sees_only_events_of_the_declared_stream() -> None:
    broker = FakeBroker()
    name = await define_stream(broker, "orders", [PAID, REFUNDED])
    # A fast core signal on an undeclared subject never meets the stream.
    await broker.publish("signals.pricetick.v1", {"n": 0})
    await broker.publish(PAID, {"n": 1})
    await broker.publish(REFUNDED, {"n": 2})

    got = [dict(m.payload) async for m in broker.replay(name, ">")]

    assert got == [{"n": 1}, {"n": 2}]


async def test_a_wildcard_stream_subject_captures_concrete_publishes() -> None:
    broker = FakeBroker()
    name = await define_stream(broker, "orders", ["orders.*.v1"])
    # JetStream retains every concrete subject the pattern covers; the
    # fake must match that, not compare subjects as plain strings.
    await broker.publish(PAID, {"n": 1})

    got = [dict(m.payload) async for m in broker.replay(name, PAID)]

    assert got == [{"n": 1}]


async def test_publishes_before_the_declaration_are_not_retained() -> None:
    broker = FakeBroker()
    await broker.publish(PAID, {"n": 0})

    name = await define_stream(broker, "orders", [PAID])
    # A second declaration is a no-op: it never widens retention.
    await define_stream(broker, "orders", [PAID])
    await broker.publish(PAID, {"n": 1})

    got = [dict(m.payload) async for m in broker.replay(name, PAID)]

    assert got == [{"n": 1}]


async def test_replay_of_an_undefined_stream_fails_loud() -> None:
    broker = FakeBroker()

    with pytest.raises(MessagingError):
        async for _ in broker.replay("orders", ">"):
            pass


async def test_replay_after_a_dropped_stream_fails_loud() -> None:
    broker = FakeBroker()
    name = await define_stream(broker, "orders", [PAID])
    await broker.publish(PAID, {"n": 1})

    await broker.drop_stream(name)

    with pytest.raises(MessagingError):
        async for _ in broker.replay(name, PAID):
            pass


async def test_define_stream_rejects_bad_names_and_retention() -> None:
    broker = FakeBroker()

    with pytest.raises(ValueError):
        await define_stream(broker, "bad domain", [PAID])
    with pytest.raises(ValueError):
        await define_stream(broker, "orders", ["bad subject"])
    with pytest.raises(ValueError):
        await define_stream(broker, "orders", [PAID], retention="bogus")
