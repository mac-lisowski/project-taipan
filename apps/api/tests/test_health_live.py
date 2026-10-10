"""Live proof: /health against a real NATS broker.

Skip when the broker is unreachable, same convention as
test_kvstore_live.py. What only a live run proves: the cached flag is
False before first use, flips True after a real connect, and /health
mirrors both. The compose nats service from docker-compose.yaml
provides the broker; the test skips when it is not running.
"""

import os
import socket
from urllib.parse import urlsplit

import httpx2 as httpx
import pytest
from api.main import app, lifespan

BROKER_URL = os.environ.get("API_BROKER_URL", "nats://localhost:4222")


def _reachable() -> bool:
    parts = urlsplit(BROKER_URL)
    target = (parts.hostname or "localhost", parts.port or 4222)
    try:
        with socket.create_connection(target, timeout=2):
            return True
    except OSError:
        return False


live_only = pytest.mark.skipif(not _reachable(), reason="nats not reachable")


@pytest.mark.anyio
@live_only
async def test_health_flips_true_after_first_use(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_BROKER_URL", BROKER_URL)
    monkeypatch.delenv("API_AUTO_MIGRATE", raising=False)
    async with lifespan(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            # Never used yet: build and boot alone never open the link.
            before = await ac.get("/health")
            seam = app.state.messaging
            await seam.publish("events.health.probe", {"ok": True})
            after = await ac.get("/health")
            await seam.drain()

    assert before.status_code == 200
    assert before.json() == {"status": "ok", "broker": {"connected": False}}
    assert after.json() == {"status": "ok", "broker": {"connected": True}}
