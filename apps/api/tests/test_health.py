"""Health endpoint: brokerless boot truth. Unit tier, no broker needed."""

import socket

import pytest
from api.main import app
from fastapi.testclient import TestClient
from messaging import FakeBroker

# The spec pins the shape: app status plus broker connected flag.
BROKER_DOWN = {"status": "ok", "broker": {"connected": False}}
BROKER_UP = {"status": "ok", "broker": {"connected": True}}


def _closed_port_url() -> str:
    # A just-freed port refuses connects at once, whatever the env runs.
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return f"nats://127.0.0.1:{probe.getsockname()[1]}"


def _boot(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.delenv("API_AUTO_MIGRATE", raising=False)
    return TestClient(app)


def test_boots_with_unreachable_broker_and_health_says_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_BROKER_URL", _closed_port_url())
    with _boot(monkeypatch) as test_client:
        resp = test_client.get("/health")

    # Lifespan entered without error: boot never waits on the broker.
    assert resp.status_code == 200
    assert resp.json() == BROKER_DOWN


def test_health_mirrors_a_connected_link(monkeypatch: pytest.MonkeyPatch) -> None:
    # The fake is the seam's own test double: it reports connected True.
    monkeypatch.setattr("api.main.build_messaging", lambda config: FakeBroker())
    with _boot(monkeypatch) as test_client:
        resp = test_client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == BROKER_UP
