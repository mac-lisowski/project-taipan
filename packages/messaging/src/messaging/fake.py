"""Fake adapter: in-memory broker, no network."""

import asyncio
from collections import deque
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, field
from typing import Any

from messaging.seam import Handler, Message, Messaging, MessagingError, Settle


@dataclass
class _Subscription:
    subject: str
    handler: Handler
    queue: str


@dataclass
class _Pool:
    """One durable work pool: shared cap and dead-letter subject."""

    max_deliver: int
    dead_letter: str
    handlers: list[Handler] = field(default_factory=list)
    cursor: int = 0
    inflight: deque[tuple[Message, int]] = field(default_factory=deque)


@dataclass
class _Stream:
    """One declared domain stream: subjects plus its retention start."""

    name: str
    subjects: tuple[str, ...]
    retention: str
    start: int


def _matches(pattern: str, subject: str) -> bool:
    # NATS wildcard grammar: * spans one token, > spans the rest.
    pat, sub = pattern.split("."), subject.split(".")
    for i, token in enumerate(pat):
        if token == ">":
            return True
        if i >= len(sub) or (token != "*" and token != sub[i]):
            return False
    return len(pat) == len(sub)


class FakeBroker(Messaging):
    """Captures publishes in memory and delivers to local subscribers."""

    def __init__(self) -> None:
        self._subs: list[_Subscription] = []
        self._pools: dict[tuple[str, str], _Pool] = {}
        self._streams: dict[str, _Stream] = {}
        self._published: list[Message] = []
        self._drained = False
        # One rotation cursor per queue group; plain subs share the "" group.
        self._next: dict[tuple[str, str], int] = {}
        self._tasks: set[asyncio.Task] = set()

    @property
    def connected(self) -> bool:
        # The fake never disconnects: dev and tests need no broker.
        return True

    async def publish(self, subject: str, payload: Mapping[str, Any]) -> None:
        # Copy on publish so later caller edits cannot change delivery.
        msg = Message(subject=subject, payload=dict(payload))
        self._published.append(msg)
        if self._drained:
            return
        for queue in sorted({s.queue for s in self._subs if s.subject == subject}):
            members = [s for s in self._subs if s.subject == subject and s.queue == queue]
            if queue:
                # A work queue: one member of the group takes each publish.
                key = (subject, queue)
                index = self._next.get(key, 0) % len(members)
                self._next[key] = self._next.get(key, 0) + 1
                await members[index].handler(msg)
            else:
                # A plain subscription: every member sees every publish.
                for member in members:
                    await member.handler(msg)
        for (pool_subject, _), pool in self._pools.items():
            if pool_subject == subject and pool.handlers:
                pool.inflight.append((msg, 0))
                self._dispatch(pool)

    async def subscribe(self, subject: str, handler: Handler, *, queue: str = "") -> None:
        self._subs.append(_Subscription(subject=subject, handler=handler, queue=queue))

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
        # Pool settings come from the first member; the group is the set
        # of handlers on one durable name, so queue names stay unused.
        key = (subject, durable)
        pool = self._pools.get(key)
        if pool is None:
            pool = _Pool(max_deliver=max_deliver, dead_letter=dead_letter)
            self._pools[key] = pool
        pool.handlers.append(handler)

    async def ensure_stream(
        self,
        name: str,
        subjects: list[str],
        retention: str = "limits",
    ) -> None:
        # Idempotent: a second declaration keeps the first retention start.
        if name not in self._streams:
            self._streams[name] = _Stream(name, tuple(subjects), retention, len(self._published))

    async def drop_stream(self, name: str) -> None:
        self._streams.pop(name, None)

    async def replay(self, stream: str, pattern: str) -> AsyncIterator[Message]:
        try:
            entry = self._streams[stream]
        except KeyError:
            raise MessagingError(f"stream {stream} is not defined") from None
        # Snapshot: a publish during replay cannot reshape this walk.
        for msg in list(self._published)[entry.start :]:
            # Membership uses the same wildcard grammar as the replay
            # filter: a declared pattern captures what JetStream would.
            if any(_matches(s, msg.subject) for s in entry.subjects) and _matches(
                pattern, msg.subject
            ):
                # Copy on replay so later caller edits cannot change it.
                yield Message(
                    subject=msg.subject,
                    payload=dict(msg.payload),
                )

    async def drain(self) -> None:
        # Drain ends delivery but keeps capture, so late traffic stays visible.
        self._drained = True
        self._subs.clear()
        self._pools.clear()

    def list_published(self) -> list[Message]:
        return list(self._published)

    def clear(self) -> None:
        """Reset to a fresh broker: capture, subscriptions, and drain state."""
        self._published.clear()
        self._subs.clear()
        self._pools.clear()
        self._streams.clear()
        self._next.clear()
        self._drained = False

    def _dispatch(self, pool: _Pool) -> None:
        # Attempts run as tasks: a nak from inside a handler cannot
        # recurse the publish call that started the job.
        while pool.inflight and not self._drained:
            msg, attempts = pool.inflight.popleft()
            task = asyncio.create_task(self._attempt(pool, msg, attempts))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    async def _attempt(self, pool: _Pool, msg: Message, attempts: int) -> None:
        handler = pool.handlers[pool.cursor % len(pool.handlers)]
        pool.cursor += 1
        job = Message(
            subject=msg.subject,
            payload=msg.payload,
            settle=self._settle_route(pool, msg, attempts),
        )
        try:
            await handler(job)
        except Exception:  # noqa: BLE001 - a crashing handler is a failed job
            await self._fail(pool, msg, attempts, 0.0)

    def _settle_route(self, pool: _Pool, msg: Message, attempts: int) -> Settle:
        async def settle(action: str, delay: float) -> None:
            if action == "ack":
                return
            await self._fail(pool, msg, attempts, delay)

        return settle

    async def _fail(self, pool: _Pool, msg: Message, attempts: int, delay: float) -> None:
        if self._drained:
            return
        runs_used = attempts + 1
        if runs_used < pool.max_deliver:
            if delay > 0:
                await asyncio.sleep(delay)
            pool.inflight.append((msg, runs_used))
            self._dispatch(pool)
            return
        if pool.dead_letter:
            # One raw copy per expired job, on the domain DLQ subject.
            await self.publish(pool.dead_letter, dict(msg.payload))
