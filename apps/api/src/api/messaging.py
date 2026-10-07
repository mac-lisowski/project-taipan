"""Messaging composition root: pick the broker adapter once from config."""

from __future__ import annotations

from fastapi import Request
from messaging import Messaging, NatsBroker

from api.config import Config, get_config


def build_messaging(
    config: Config | None = None,
    *,
    adapter: Messaging | None = None,
) -> Messaging:
    """Build the broker adapter once at composition time.

    An injected adapter wins, so tests keep the in-memory fake. The
    default is the real NATS adapter: it builds without connecting and
    fails only when a route actually uses the broker. Config owns the
    URL and the JetStream store mode.
    """
    if adapter is not None:
        return adapter
    cfg = config or get_config()
    return NatsBroker(cfg.msg.broker_url, store=cfg.msg.jetstream_store)


def get_messaging(request: Request) -> Messaging:
    """Route dependency. App code receives the interface only."""
    return request.app.state.messaging
