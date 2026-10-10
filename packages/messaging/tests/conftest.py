"""Shared live-test scaffolding: broker probe, factory, teardown.

One inspector link, one broker factory, and one teardown loop for the
live files, so per-run streams never survive a test run.
"""

import asyncio
import contextlib
import os
import socket
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Any
from urllib.parse import urlsplit

import nats
import pytest
from messaging import NatsBroker
from nats.errors import Error as NatsError

BROKER_URL = os.environ.get("API_BROKER_URL", "nats://localhost:4222")


def _reachable(url: str) -> bool:
    parts = urlsplit(url)
    host = parts.hostname or "localhost"
    port = parts.port or 4222
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


class Inspector:
    """One inspector link plus per-run names and teardown tracking."""

    def __init__(self, js: Any) -> None:
        self.js = js
        self.streams: list[str] = []

    def stream(self) -> str:
        name = f"taipan_live_{uuid.uuid4().hex[:12]}"
        self.streams.append(name)
        return name

    def subject(self) -> str:
        return f"events.live.{uuid.uuid4().hex[:12]}"


def _make_broker(store: str = "memory") -> NatsBroker:
    # Memory store keeps the run off the server disk, per the spec.
    return NatsBroker(BROKER_URL, store=store, connect_timeout=2)


@pytest.fixture
def reachable() -> Callable[[str], bool]:
    """TCP probe for one URL, so a test can skip a service it alone needs."""
    return _reachable


@pytest.fixture
def broker_factory() -> Callable[..., NatsBroker]:
    return _make_broker


@pytest.fixture
async def inspector() -> AsyncIterator[Inspector]:
    """One JetStream inspector per test; tracked streams are torn down."""
    if not _reachable(BROKER_URL):
        pytest.skip("nats broker not reachable")
    link = await nats.connect(BROKER_URL)
    live = Inspector(link.jetstream())
    yield live
    for name in live.streams:
        # Best effort teardown: a dead link must not mask the test result.
        with contextlib.suppress(NatsError, OSError, asyncio.TimeoutError):
            await live.js.delete_stream(name)
    await link.close()
