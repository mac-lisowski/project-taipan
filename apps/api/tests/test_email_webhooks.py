"""Resend bounce webhook intake: Svix verify, kind mapping, replay dedupe."""

import base64
import hashlib
import hmac
import json
import time

import pytest
from api.routers.email_webhooks import router
from email_delivery import (
    FakeEmailSender,
    GuardedEmailSender,
    MemorySuppressionStore,
    PostgresSuppressionStore,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient

SECRET = "whsec_" + base64.b64encode(b"test-secret-key-123456789012").decode()
WRONG_SECRET = "whsec_" + base64.b64encode(b"wrong-secret-key-1234567890").decode()
ADDRESS = "bounced@example.com"


def _sign(secret: str, msg_id: str, timestamp: str, body: bytes) -> str:
    """Stubbed signer mirroring the Svix HMAC scheme the route verifies."""
    key = base64.b64decode(secret.removeprefix("whsec_"))
    digest = hmac.new(key, f"{msg_id}.{timestamp}.".encode() + body, hashlib.sha256).digest()
    return "v1," + base64.b64encode(digest).decode()


def _headers(msg_id: str, body: bytes, secret: str = SECRET, age: int = 0) -> dict[str, str]:
    timestamp = str(int(time.time()) - age)
    return {
        "svix-id": msg_id,
        "svix-timestamp": timestamp,
        "svix-signature": _sign(secret, msg_id, timestamp, body),
    }


def _body(event_type: str = "email.bounced", bounce: str = "hard") -> bytes:
    data: dict = {"to": [ADDRESS]}
    if event_type == "email.bounced":
        data["bounce"] = {"type": bounce}
    return json.dumps({"type": event_type, "data": data}).encode()


def _memory_client(monkeypatch: pytest.MonkeyPatch, secret: str = SECRET) -> TestClient:
    monkeypatch.setenv("API_RESEND_WEBHOOK_SECRET", secret)
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.state.email_sender = GuardedEmailSender(FakeEmailSender(), MemorySuppressionStore())
    return TestClient(app)


def _post(client: TestClient, body: bytes, headers: dict[str, str]):
    return client.post(
        "/api/email/webhooks/resend",
        content=body,
        headers={**headers, "content-type": "application/json"},
    )


def test_hard_bounce_suppresses(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _memory_client(monkeypatch)
    body = _body("email.bounced", "hard")

    resp = _post(client, body, _headers("evt-1", body))

    assert resp.status_code == 200
    assert resp.json() == {"status": "recorded", "suppressed": True}
    assert client.app.state.email_sender.store.is_suppressed(ADDRESS)


def test_soft_bounce_counts_without_suppressing(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _memory_client(monkeypatch)
    body = _body("email.bounced", "soft")

    resp = _post(client, body, _headers("evt-1", body))

    assert resp.status_code == 200
    assert resp.json() == {"status": "recorded", "suppressed": False}
    assert not client.app.state.email_sender.store.is_suppressed(ADDRESS)


def test_complaint_suppresses(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _memory_client(monkeypatch)
    body = _body("email.complained")

    resp = _post(client, body, _headers("evt-1", body))

    assert resp.status_code == 200
    assert resp.json() == {"status": "recorded", "suppressed": True}
    assert client.app.state.email_sender.store.is_suppressed(ADDRESS)


def test_bad_signature_is_401_with_no_state_change(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _memory_client(monkeypatch)
    body = _body()

    resp = _post(client, body, _headers("evt-1", body, secret=WRONG_SECRET))

    assert resp.status_code == 401
    assert not client.app.state.email_sender.store.is_suppressed(ADDRESS)


def test_missing_headers_is_401(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _memory_client(monkeypatch)

    resp = client.post("/api/email/webhooks/resend", json={"type": "email.bounced"})

    assert resp.status_code == 401


def test_stale_timestamp_is_401(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _memory_client(monkeypatch)
    body = _body()

    resp = _post(client, body, _headers("evt-1", body, age=600))

    assert resp.status_code == 401
    assert not client.app.state.email_sender.store.is_suppressed(ADDRESS)


def test_empty_secret_rejects_everything(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _memory_client(monkeypatch, secret="")
    body = _body()

    resp = _post(client, body, _headers("evt-1", body, secret=""))

    assert resp.status_code == 401
    assert not client.app.state.email_sender.store.is_suppressed(ADDRESS)


def test_corrupt_but_signed_body_is_401(monkeypatch: pytest.MonkeyPatch) -> None:
    # Accepted conflation: the SDK raises one ValueError for bad JSON
    # and bad signatures alike, so both map to 401, never 500.
    client = _memory_client(monkeypatch)
    body = b"{not json"
    headers = _headers("evt-bad", body)

    resp = _post(client, body, headers)

    assert resp.status_code == 401
    assert not client.app.state.email_sender.store.is_suppressed(ADDRESS)


def test_unknown_kind_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _memory_client(monkeypatch)
    body = _body("email.opened")

    resp = _post(client, body, _headers("evt-1", body))

    assert resp.status_code == 200
    assert resp.json() == {"status": "ignored"}
    assert not client.app.state.email_sender.store.is_suppressed(ADDRESS)


def test_unknown_bounce_subtype_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _memory_client(monkeypatch)
    body = _body("email.bounced", "fuzzy")

    resp = _post(client, body, _headers("evt-1", body))

    assert resp.status_code == 200
    assert resp.json() == {"status": "ignored"}
    assert not client.app.state.email_sender.store.is_suppressed(ADDRESS)


def test_replay_is_noop_with_same_outcome(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _memory_client(monkeypatch)
    body = _body()

    first = _post(client, body, _headers("evt-1", body))
    second = _post(client, body, _headers("evt-1", body))

    assert first.status_code == 200
    assert second.json() == first.json() == {"status": "recorded", "suppressed": True}


def test_replay_against_postgres_is_noop(engine, session_factory, monkeypatch) -> None:
    monkeypatch.setenv("API_RESEND_WEBHOOK_SECRET", SECRET)
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.state.email_sender = GuardedEmailSender(
        FakeEmailSender(), PostgresSuppressionStore(session_factory)
    )
    client = TestClient(app)
    body = _body()

    first = _post(client, body, _headers("evt-pg-1", body))
    second = _post(client, body, _headers("evt-pg-1", body))

    assert first.status_code == 200
    assert second.json() == first.json() == {"status": "recorded", "suppressed": True}
    assert app.state.email_sender.store.is_suppressed(ADDRESS)
