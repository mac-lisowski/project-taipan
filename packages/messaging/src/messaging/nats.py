"""NATS adapter: real broker over nats-py with lazy bounded connect."""

import asyncio
import contextlib
import json
from collections.abc import Mapping
from typing import Any

import nats
from nats.aio.client import Client as NatsClient
from nats.errors import Error as NatsError
from nats.js.api import AckPolicy, ConsumerConfig, StorageType
from nats.js.client import JetStreamContext

from messaging.nats_streams import StreamOps
from messaging.seam import STORE_MODES, Handler, Message, Messaging, MessagingError

_STORAGE = {
    "file": StorageType.FILE,
    "memory": StorageType.MEMORY,
}
# One vocabulary: seam owns the modes; this map must mirror exactly those.
assert tuple(_STORAGE) == STORE_MODES

# Seconds one worker waits for a job before it asks the queue again.
_POLL = 0.5


class NatsBroker(StreamOps, Messaging):
    """Messaging seam over one NATS server with JetStream.

    Build never connects. The first use starts one bounded connect
    attempt; a failure raises MessagingError on that use only. Later
    uses try again. `connected` reads cached client state, so boot and
    health can ask without touching the network.
    """

    def __init__(self, url: str, *, store: str = "file", connect_timeout: float = 2.0) -> None:
        if store not in _STORAGE:
            raise ValueError("store must be 'file' or 'memory'")
        self._url = url
        self._connect_timeout = connect_timeout
        self._storage = _STORAGE[store]
        self._nc: NatsClient | None = None
        self._js: JetStreamContext | None = None
        self._drained = False
        self._workers: set[asyncio.Task] = set()
        # One first-use connect attempt at a time; losers reuse its result.
        self._connecting = asyncio.Lock()

    @property
    def connected(self) -> bool:
        # Cached state only: health checks must never open a connection.
        nc = self._nc
        return nc is not None and nc.is_connected

    async def publish(self, subject: str, payload: Mapping[str, Any]) -> None:
        nc = await self._client()
        try:
            await nc.publish(subject, json.dumps(payload).encode())
        except (NatsError, OSError) as err:
            await self._drop()
            raise MessagingError(f"publish on {subject} failed: {err}") from err

    async def subscribe(self, subject: str, handler: Handler, *, queue: str = "") -> None:
        nc = await self._client()

        async def deliver(raw: Any) -> None:
            msg = Message(
                subject=raw.subject,
                payload=json.loads(raw.data),
            )
            await handler(msg)

        try:
            await nc.subscribe(subject, cb=deliver, queue=queue)
        except (NatsError, OSError) as err:
            await self._drop()
            raise MessagingError(f"subscribe to {subject} failed: {err}") from err

    async def subscribe_durable(
        self,
        subject: str,
        handler: Handler,
        *,
        durable: str,
        queue: str,
        max_deliver: int = 3,
        dead_letter: str,
    ) -> None:
        """Start one worker on the shared durable pull consumer.

        The durable consumer is the work queue: every worker on the
        same durable name fetches from it, so each job runs once per
        pool. A nak pulls the job again up to max_deliver runs; the
        last allowed run moves a failed job to the dead-letter subject.
        """
        js = await self._jetstream()
        config = ConsumerConfig(
            durable_name=durable,
            ack_policy=AckPolicy.EXPLICIT,
            max_deliver=max_deliver,
        )
        try:
            sub = await js.pull_subscribe(subject, durable=durable, config=config)
        except (NatsError, OSError) as err:
            await self._drop()
            raise MessagingError(f"durable subscribe to {subject} failed: {err}") from err
        task = asyncio.create_task(self._work(sub, handler, max_deliver, dead_letter))
        self._workers.add(task)
        task.add_done_callback(self._workers.discard)

    async def _work(
        self,
        sub: JetStreamContext.PullSubscription,
        handler: Handler,
        max_deliver: int,
        dead_letter: str,
    ) -> None:
        while not self._drained:
            try:
                raw = await sub.fetch(1, timeout=_POLL)
            except TimeoutError:
                # An empty poll: the queue has no job for this worker now.
                continue
            except (NatsError, OSError):
                # A dead link cannot feed the pool; the drop lets the
                # next use fail loud and a later subscribe rebuild it.
                await self._drop()
                return
            try:
                await self._deliver(raw[0], handler, max_deliver, dead_letter)
            except MessagingError:
                # The link died mid job and is already dropped: stop here.
                return

    async def _deliver(
        self,
        raw: Any,
        handler: Handler,
        max_deliver: int,
        dead_letter: str,
    ) -> None:
        payload = json.loads(raw.data)
        # The last allowed run moves a failed job to the DLQ subject.
        final = raw.metadata.num_delivered >= max_deliver

        async def settle(action: str, delay: float) -> None:
            if action == "ack":
                await raw.ack()
                return
            if final and dead_letter:
                await self.publish(dead_letter, payload)
                await raw.term()
                return
            await raw.nak(delay or None)

        msg = Message(
            subject=raw.subject,
            payload=payload,
            settle=settle,
        )
        try:
            await handler(msg)
        except Exception:  # noqa: BLE001 - a crashing handler is a failed job
            # Best effort only: a dead link leaves the job to ack_wait.
            with contextlib.suppress(NatsError, OSError, MessagingError):
                await settle("nak", 0.0)

    async def drain(self) -> None:
        # A never-used broker drains by doing nothing; shutdown must not
        # open a connection just to close it. The seam stays shut after
        # drain: later uses fail loud, never open a fresh link.
        self._drained = True
        for task in list(self._workers):
            task.cancel()
        if self._workers:
            await asyncio.gather(*list(self._workers), return_exceptions=True)
        if self._nc is None:
            return
        with contextlib.suppress(Exception):
            await self._nc.drain()
        await self._drop()

    async def _client(self) -> NatsClient:
        if self._drained:
            raise MessagingError("broker link is drained")
        if self.connected:
            assert self._nc is not None
            return self._nc
        async with self._connecting:
            if self.connected:
                assert self._nc is not None
                return self._nc
            stale, self._nc, self._js = self._nc, None, None
            if stale is not None:
                # A lost link keeps a half-open client; close it before
                # a fresh attempt so tasks do not pile up.
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(stale.close(), timeout=2)
            try:
                # nats-py has no retry_on_failed_connect and its connect
                # loop retries refused servers forever, so the clock
                # around it is what bounds the attempt to one shot.
                nc = await asyncio.wait_for(
                    nats.connect(self._url, connect_timeout=self._connect_timeout),
                    timeout=self._connect_timeout + 1,
                )
            except Exception as err:
                raise MessagingError(f"connect to {self._url} failed: {err}") from err
            self._nc = nc
            return nc

    async def _jetstream(self) -> JetStreamContext:
        await self._client()
        if self._js is None:
            assert self._nc is not None
            self._js = self._nc.jetstream()
        assert self._js is not None
        return self._js

    async def _drop(self) -> None:
        nc, self._nc, self._js = self._nc, None, None
        if nc is not None:
            with contextlib.suppress(Exception):
                await asyncio.wait_for(nc.close(), timeout=2)
