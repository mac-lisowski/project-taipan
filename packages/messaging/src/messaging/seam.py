"""Messaging seam: publish and subscribe over one injected broker link."""

import re
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol


class MessagingError(RuntimeError):
    """Seam failure on use: connect, publish, or subscribe broke.

    Adapters raise this instead of client errors so callers catch one
    type. Boot and health never see it because they never use the link.
    """


# One settle call per durable delivery: "ack" is done, "nak" failed
# with an optional redelivery delay in seconds.
Settle = Callable[[str, float], Awaitable[None]]


@dataclass(frozen=True)
class Message:
    """One delivered broker message: subject and small JSON payload.

    Durable deliveries carry a settle route, so the handler marks the
    job done or failed. Plain deliveries settle themselves: a settle
    call there is a wiring mistake and fails loud.
    """

    subject: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    settle: Settle | None = field(default=None, compare=False, repr=False)

    async def ack(self) -> None:
        """Settle the job as done: the broker never redelivers it."""
        if self.settle is None:
            raise MessagingError("message has no settle path: plain subs auto-settle")
        await self.settle("ack", 0.0)

    async def nak(self, delay: float = 0.0) -> None:
        """Settle the job as failed: the broker redelivers it up to the cap.

        Past the cap the job moves to the dead-letter subject instead.
        """
        if self.settle is None:
            raise MessagingError("message has no settle path: plain subs auto-settle")
        await self.settle("nak", delay)


Handler = Callable[[Message], Awaitable[None]]


def dead_letter_subject(domain: str) -> str:
    """Dead-letter subject for one domain, per the <domain>.dlq grammar."""
    _check_domain(domain)
    return f"{domain}.dlq"


# One plain name token: no dot, space, or wildcard can sneak into a name.
_TOKEN = re.compile(r"[A-Za-z0-9_-]+")

# One subject token of a declared pattern; wildcards stay whole tokens.
_PATTERN_TOKEN = re.compile(r"[A-Za-z0-9_*>-]+")


def _check_token(value: str, what: str) -> str:
    if not _TOKEN.fullmatch(value):
        raise ValueError(f"{what} {value!r} is not one token of [A-Za-z0-9_-]")
    return value


def _check_domain(domain: str) -> str:
    # A domain may span segments, but each one is a plain token.
    for token in domain.split("."):
        _check_token(token, "domain segment")
    return domain


def subject(domain: str, kind: str, version: str) -> str:
    """Build the one <domain>.<kind>.<version> subject for an event.

    Single source of the spec grammar, shared by publishers and stream
    declarations, so tests and the naming doc cannot drift apart.
    """
    _check_domain(domain)
    _check_token(kind, "kind")
    _check_token(version, "version")
    return f"{domain}.{kind}.{version}"


# Retention policies a domain stream may keep, from the JetStream set.
RETENTIONS = ("limits", "interest", "workqueue")

# Storage modes a stream may use: file for real envs, memory for tests.
STORE_MODES = ("file", "memory")


def _check_pattern(value: str, what: str) -> str:
    # A declared subject may carry whole-token wildcards, a name may not.
    if not value or not all(_PATTERN_TOKEN.fullmatch(t) for t in value.split(".")):
        raise ValueError(f"{what} {value!r} is not a dot-separated subject pattern")
    return value


def _stream_name(domain: str) -> str:
    # A stream name is one token, so a dotted domain folds into a dash.
    return _check_domain(domain).replace(".", "-")


async def define_stream(
    broker: "Messaging",
    domain: str,
    subjects: list[str],
    retention: str = "limits",
) -> str:
    """Declare the one stream of a domain and return its name.

    Safe to call again: an existing stream is left as is, so boot and
    tests can declare on every start. Retention lives on the stream,
    per domain, never in global config.
    """
    if retention not in RETENTIONS:
        raise ValueError(f"retention {retention!r} is not one of {', '.join(RETENTIONS)}")
    _check_domain(domain)
    for one in subjects:
        _check_pattern(one, "stream subject")
    name = _stream_name(domain)
    await broker.ensure_stream(name, subjects, retention)
    return name


class Messaging(Protocol):
    """Single seam for all broker traffic. Adapters implement this."""

    @property
    def connected(self) -> bool:
        """True while the adapter can deliver traffic."""
        ...

    async def publish(self, subject: str, payload: Mapping[str, Any]) -> None:
        """Publish one small JSON payload on a subject."""
        ...

    async def subscribe(self, subject: str, handler: Handler, *, queue: str = "") -> None:
        """Start calling handler for matching subjects.

        An empty queue is a plain subscription: every publish reaches
        it. A shared queue name forms a group: each publish reaches
        one member of the group.
        """
        ...

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
        """Run handler as one member of a durable work pool.

        The pool shares the durable name and the queue group, so each
        publish runs once per pool. A nak pulls the job again, up to
        max_deliver runs. Past the cap the job moves once to the
        dead-letter subject, so a bad job never blocks the queue.
        The caller picks the dead-letter subject, so overflow never
        drops silently.
        """
        ...

    async def ensure_stream(
        self,
        name: str,
        subjects: list[str],
        retention: str = "limits",
    ) -> None:
        """Create the named stream over the subjects if it is missing."""
        ...

    async def drop_stream(self, name: str) -> None:
        """Delete the stream and its stored messages."""
        ...

    def replay(self, stream: str, pattern: str) -> AsyncIterator[Message]:
        """Iterate a stream's retained events for a subject filter.

        The read starts at the oldest retained event and never stores
        state on the broker, so many late readers can replay at once.
        """
        ...

    async def drain(self) -> None:
        """Stop delivery gracefully. Publishes after drain are not delivered."""
        ...
