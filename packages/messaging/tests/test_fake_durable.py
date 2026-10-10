"""FakeBroker durable queues: pool delivery, ack/nak, cap, dead letter.

The fake pins the whole work-queue contract brokerless: one run per
pool per job, redelivery on nak up to the cap, one dead-letter copy
past the cap, and a queue that never blocks on a poisoned job.
"""

import asyncio

import pytest
from messaging import FakeBroker, Message, MessagingError, dead_letter_subject

pytestmark = pytest.mark.anyio


async def test_pool_runs_one_job_once_per_publish() -> None:
    broker = FakeBroker()
    runs: list[str] = []
    done = asyncio.Event()

    async def work(msg: Message) -> None:
        runs.append(msg.subject)
        await msg.ack()
        done.set()

    await broker.subscribe_durable(
        "jobs.mail",
        work,
        durable="mail-workers",
        queue="mailers",
        dead_letter="",
    )
    await broker.subscribe_durable(
        "jobs.mail",
        work,
        durable="mail-workers",
        queue="mailers",
        dead_letter="",
    )
    await broker.publish("jobs.mail", {"to": "ada@example.com"})
    await asyncio.wait_for(done.wait(), 1)

    # The pool shares one durable: a second member never reruns the job.
    assert runs == ["jobs.mail"]


async def test_nak_redelivers_the_same_job_until_acked() -> None:
    broker = FakeBroker()
    runs: list[int] = []
    settled = asyncio.Event()

    async def flaky(msg: Message) -> None:
        runs.append(msg.payload["n"])
        if len(runs) < 2:
            await msg.nak()
        else:
            await msg.ack()
            settled.set()

    await broker.subscribe_durable("jobs.mail", flaky, durable="m", queue="q", dead_letter="")
    await broker.publish("jobs.mail", {"n": 1})
    await asyncio.wait_for(settled.wait(), 1)

    assert runs == [1, 1]


async def test_cap_exhaustion_moves_the_job_to_the_dead_letter_subject() -> None:
    broker = FakeBroker()
    runs = 0
    buried = asyncio.Event()
    buried_msgs: list[Message] = []

    async def poison(msg: Message) -> None:
        nonlocal runs
        runs += 1
        await msg.nak()

    async def bury(msg: Message) -> None:
        buried_msgs.append(msg)
        buried.set()

    await broker.subscribe(dead_letter_subject("jobs"), bury)
    await broker.subscribe_durable(
        "jobs.mail",
        poison,
        durable="m",
        queue="q",
        max_deliver=2,
        dead_letter=dead_letter_subject("jobs"),
    )
    await broker.publish("jobs.mail", {"job": "bad"})
    await asyncio.wait_for(buried.wait(), 1)

    # The cap allows exactly two runs, then one DLQ copy, never a third run.
    assert runs == 2
    [dead] = buried_msgs
    assert dict(dead.payload) == {"job": "bad"}
    assert dead.subject == dead_letter_subject("jobs")


async def test_queue_stays_open_after_a_poisoned_job() -> None:
    broker = FakeBroker()
    buried = asyncio.Event()
    good_done = asyncio.Event()
    good_runs: list[dict] = []

    async def poison(msg: Message) -> None:
        await msg.nak()

    async def good(msg: Message) -> None:
        good_runs.append(dict(msg.payload))
        await msg.ack()
        good_done.set()

    async def bury(msg: Message) -> None:
        buried.set()

    await broker.subscribe(dead_letter_subject("jobs"), bury)
    await broker.subscribe_durable(
        "jobs.mail",
        poison,
        durable="m",
        queue="q",
        max_deliver=1,
        dead_letter=dead_letter_subject("jobs"),
    )
    await broker.publish("jobs.mail", {"job": "bad"})
    await asyncio.wait_for(buried.wait(), 1)

    await broker.subscribe_durable("jobs.mail", good, durable="m", queue="q", dead_letter="")
    await broker.publish("jobs.mail", {"job": "fine"})
    await asyncio.wait_for(good_done.wait(), 1)

    assert good_runs == [{"job": "fine"}]


async def test_settle_on_a_plain_subscription_message_raises() -> None:
    broker = FakeBroker()
    got: list[Message] = []
    arrived = asyncio.Event()

    async def capture(msg: Message) -> None:
        got.append(msg)
        arrived.set()

    await broker.subscribe("events.order.paid", capture)
    await broker.publish("events.order.paid", {"order_id": 1})
    await asyncio.wait_for(arrived.wait(), 1)

    [msg] = got
    with pytest.raises(MessagingError):
        await msg.ack()


def test_dead_letter_subject_uses_the_domain_grammar() -> None:
    assert dead_letter_subject("jobs") == "jobs.dlq"
