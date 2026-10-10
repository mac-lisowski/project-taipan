"""App wiring: the API boots brokerless and hands out one messaging seam."""

import pytest
from api.config import Config
from api.main import app
from api.messaging import build_messaging, get_messaging
from fastapi import Request
from fastapi.testclient import TestClient
from messaging import FakeBroker, NatsBroker


def test_default_adapter_is_the_nats_broker() -> None:
    broker = build_messaging(Config.from_env({}))

    assert isinstance(broker, NatsBroker)
    # Building never connects: boot must not wait on the broker.
    assert broker.connected is False


def test_fake_broker_stays_an_explicit_choice() -> None:
    fake = FakeBroker()

    assert build_messaging(Config.from_env({}), adapter=fake) is fake


def test_app_boots_and_serves_with_no_broker(monkeypatch: pytest.MonkeyPatch) -> None:
    # No broker listens anywhere in this environment; boot must not wait.
    monkeypatch.delenv("API_AUTO_MIGRATE", raising=False)
    with TestClient(app) as test_client:
        resp = test_client.get("/")

    assert resp.status_code == 200


@pytest.mark.anyio
async def test_lifespan_stores_a_never_connected_seam(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from api.main import lifespan

    monkeypatch.delenv("API_AUTO_MIGRATE", raising=False)
    async with lifespan(app):
        seam = app.state.messaging

    assert isinstance(seam, NatsBroker)
    assert seam.connected is False


@pytest.mark.anyio
async def test_get_messaging_returns_the_app_state_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from api.main import lifespan

    monkeypatch.delenv("API_AUTO_MIGRATE", raising=False)
    async with lifespan(app):
        request = Request(scope={"type": "http", "app": app})
        handed_out = get_messaging(request)

    assert handed_out is app.state.messaging
