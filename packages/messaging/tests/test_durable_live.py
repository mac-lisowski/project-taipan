"""Live contract: durable work queues against a real broker.

Skip when the broker is unreachable, same convention as the redis live
tests. What only a live run proves: a shared durable serves a pool one
run per job, ack never redelivers, nak redelivers, and the last nak
lands the raw job on the domain dead-letter subject. Stream, subject,
and consumer names are unique per run and torn down, so runs leave no
server state behind.
"""

import asyncio
import uuid
from typing import Any

import pytest
from messaging import Message, dead_letter_subject

WAIT = 5.0
WINDOW = 1.0  # bounded wait that proves the absence of a redelivery


class Live:
    """Per-run domain namespace on the shared inspector link."""

    def __init__(self, inspector: Any) -> None:
        self.js = inspector.js
        self.name = f"jobs.{uuid.uuid4().hex[:12]}"
        self.stream = inspector.stream()
        self.durable = f"dv_{uuid.uuid4().hex[:12]}"

    @property
    def subject(self) -> str:
        return f"{self.name}.mail"

    @property
    def dead_letter(self) -> str:
        return dead_letter_subject(self.name)


@pytest.fixture
async def live_ctx(inspector: Any) -> Any:
    return Live(inspector)


@pytest.mark.anyio
async def test_pool_delivers_each_job_to_one_worker(live_ctx: Live, broker_factory: Any) -> None:
    broker = broker_factory()
    await broker.ensure_stream(live_ctx.stream, [live_ctx.subject])
    done = asyncio.Event()
    runs: list[str] = []

    async def work(msg: Message) -> None:
        runs.append(msg.payload["job"])
        await msg.ack()
        if len(runs) == 3:
            done.set()

    await broker.subscribe_durable(
        live_ctx.subject,
        work,
        durable=live_ctx.durable,
        queue="pool",
        dead_letter="",
    )
    await broker.subscribe_durable(
        live_ctx.subject,
        work,
        durable=live_ctx.durable,
        queue="pool",
        dead_letter="",
    )
    for job in ("a", "b", "c"):
        await broker.publish(live_ctx.subject, {"job": job})
    await asyncio.wait_for(done.wait(), timeout=WAIT)
    await broker.drain()

    # Three publishes, three runs: no pool member ran a job twice.
    assert sorted(runs) == ["a", "b", "c"]


@pytest.mark.anyio
async def test_acked_job_never_redelivers(live_ctx: Live, broker_factory: Any) -> None:
    broker = broker_factory()
    await broker.ensure_stream(live_ctx.stream, [live_ctx.subject])
    runs: list[str] = []
    first = asyncio.Event()
    marker = asyncio.Event()
    redelivered = asyncio.Event()

    async def work(msg: Message) -> None:
        job = msg.payload["job"]
        runs.append(job)
        if len(runs) > 2:
            redelivered.set()
        await msg.ack()
        if job == "one":
            first.set()
        else:
            marker.set()

    await broker.subscribe_durable(
        live_ctx.subject,
        work,
        durable=live_ctx.durable,
        queue="pool",
        dead_letter="",
    )
    await broker.publish(live_ctx.subject, {"job": "one"})
    await asyncio.wait_for(first.wait(), timeout=WAIT)
    # A later healthy job bounds the wait: a lost ack would requeue "one".
    await broker.publish(live_ctx.subject, {"job": "two"})
    await asyncio.wait_for(marker.wait(), timeout=WAIT)
    # The window also lets the server settle both acks before the read.
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(redelivered.wait(), timeout=WINDOW)
    await broker.drain()

    # The server holds no unacked job: ack ended the job for good.
    info = await live_ctx.js.consumer_info(live_ctx.stream, live_ctx.durable)
    assert info.num_ack_pending == 0
    assert runs == ["one", "two"]


@pytest.mark.anyio
async def test_nak_redelivers_until_the_handler_acks(live_ctx: Live, broker_factory: Any) -> None:
    broker = broker_factory()
    await broker.ensure_stream(live_ctx.stream, [live_ctx.subject])
    runs = 0
    settled = asyncio.Event()

    async def flaky(msg: Message) -> None:
        nonlocal runs
        runs += 1
        if runs < 2:
            await msg.nak()
        else:
            await msg.ack()
            settled.set()

    await broker.subscribe_durable(
        live_ctx.subject,
        flaky,
        durable=live_ctx.durable,
        queue="pool",
        dead_letter="",
    )
    await broker.publish(live_ctx.subject, {"job": "flaky"})
    await asyncio.wait_for(settled.wait(), timeout=WAIT)
    await broker.drain()

    assert runs == 2


@pytest.mark.anyio
async def test_cap_overflow_lands_the_job_on_the_dead_letter_subject(
    live_ctx: Live, broker_factory: Any
) -> None:
    broker = broker_factory()
    await broker.ensure_stream(live_ctx.stream, [live_ctx.subject])
    runs = 0
    final_run = asyncio.Event()
    buried = asyncio.Event()
    dead: list[Message] = []
    unblocked = asyncio.Event()

    async def work(msg: Message) -> None:
        nonlocal runs
        if msg.payload["job"] != "poison":
            await msg.ack()
            unblocked.set()
            return
        runs += 1
        if runs >= 2:
            # The last allowed delivery: the next nak must dead-letter.
            final_run.set()
        await msg.nak()

    async def bury(msg: Message) -> None:
        dead.append(msg)
        buried.set()

    await broker.subscribe(live_ctx.dead_letter, bury)
    await broker.subscribe_durable(
        live_ctx.subject,
        work,
        durable=live_ctx.durable,
        queue="pool",
        max_deliver=2,
        dead_letter=live_ctx.dead_letter,
    )
    await broker.publish(live_ctx.subject, {"job": "poison"})
    await asyncio.wait_for(final_run.wait(), timeout=WAIT)
    await asyncio.wait_for(buried.wait(), timeout=WAIT)

    # The poisoned job is gone from the queue: the next job runs at once.
    await broker.publish(live_ctx.subject, {"job": "after"})
    await asyncio.wait_for(unblocked.wait(), timeout=WAIT)
    await broker.drain()

    assert runs == 2
    [msg] = dead
    assert dict(msg.payload) == {"job": "poison"}
    assert msg.subject == live_ctx.dead_letter
