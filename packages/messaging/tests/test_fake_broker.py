"""FakeBroker seam tests: delivery, payload shape, drain. No network."""

import pytest
from messaging import FakeBroker, Message

pytestmark = pytest.mark.anyio


async def test_one_publish_reaches_every_plain_subscriber() -> None:
    broker = FakeBroker()
    seen: list[str] = []

    async def remember(msg: Message) -> None:
        seen.append(msg.subject)

    await broker.subscribe("events.user.created", remember)
    await broker.subscribe("events.user.created", remember)
    await broker.publish("events.user.created", {"user_id": 7})

    assert seen == ["events.user.created", "events.user.created"]


async def test_other_subjects_do_not_reach_the_subscriber() -> None:
    broker = FakeBroker()
    seen: list[Message] = []

    async def capture(msg: Message) -> None:
        seen.append(msg)

    await broker.subscribe("events.order.paid", capture)
    await broker.publish("events.order.refunded", {"order_id": 1})

    assert seen == []


async def test_payload_round_trips_as_a_mapping() -> None:
    broker = FakeBroker()
    received: list[Message] = []

    async def capture(msg: Message) -> None:
        received.append(msg)

    await broker.subscribe("events.order.paid", capture)
    payload = {"order_id": 42, "total_cents": 1999}
    await broker.publish("events.order.paid", payload)
    # Later caller edits must not leak into the delivered message.
    payload["order_id"] = 0

    [msg] = received
    assert dict(msg.payload) == {"order_id": 42, "total_cents": 1999}
    assert msg.subject == "events.order.paid"


async def test_queue_group_gets_one_delivery_per_publish() -> None:
    broker = FakeBroker()
    workers: list[str] = []

    async def work_a(msg: Message) -> None:
        workers.append("a")

    async def work_b(msg: Message) -> None:
        workers.append("b")

    await broker.subscribe("jobs.mail", work_a, queue="mailers")
    await broker.subscribe("jobs.mail", work_b, queue="mailers")
    await broker.publish("jobs.mail", {"to": "ada@example.com"})

    # The group runs the job once; which member ran is not pinned.
    assert len(workers) == 1
    assert workers[0] in ("a", "b")


async def test_drain_stops_delivery() -> None:
    broker = FakeBroker()
    seen: list[Message] = []

    async def capture(msg: Message) -> None:
        seen.append(msg)

    await broker.subscribe("events.order.paid", capture)
    await broker.drain()
    await broker.publish("events.order.paid", {"order_id": 1})

    assert seen == []
    # Drain ends delivery, not capture: late traffic stays inspectable.
    assert len(broker.list_published()) == 1


async def test_clear_empties_the_capture() -> None:
    broker = FakeBroker()
    await broker.publish("events.order.paid", {"order_id": 1})

    broker.clear()

    assert broker.list_published() == []


async def test_fake_is_connected_without_a_broker() -> None:
    broker = FakeBroker()

    assert broker.connected is True
