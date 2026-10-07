"""App wiring: adapter choice from server config, keys stay server side."""

import pytest
from api.config import DEFAULT_MAIL_FROM, Config
from api.mail import build_email_sender
from email_delivery import FakeEmailSender, GuardedEmailSender, ResendEmailSender
from email_delivery.sender import SendStatus


class StubTransport:
    """Records payloads, no network. Mirrors the package test seam."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def post_email(self, payload: dict) -> None:
        self.calls.append(payload)


def test_mail_config_defaults_to_fake() -> None:
    cfg = Config.from_env({})

    assert cfg.mail.resend_api_key == ""
    assert cfg.mail.mail_from_address == DEFAULT_MAIL_FROM


def test_blank_from_with_key_fails_loud() -> None:
    with pytest.raises(ValueError, match="API_MAIL_FROM"):
        Config.from_env({"API_RESEND_API_KEY": "re_test_key", "API_MAIL_FROM": "  "})


def test_no_key_selects_guarded_fake_adapter() -> None:
    sender = build_email_sender(Config.from_env({}))

    assert isinstance(sender, GuardedEmailSender)
    assert isinstance(sender.inner, FakeEmailSender)


def test_fake_adapter_captures_mail_without_network() -> None:
    sender = build_email_sender(Config.from_env({}))
    assert isinstance(sender, GuardedEmailSender)
    assert isinstance(sender.inner, FakeEmailSender)

    result = sender.send(
        "activation", "ada@example.com", {"app_name": "Taipan", "link": "https://x/y"}
    )

    assert result.status is SendStatus.SENT
    [captured] = sender.inner.list_sent()
    assert captured.template == "activation"
    assert captured.recipient == "ada@example.com"


def test_composed_sender_applies_suppression() -> None:
    sender = build_email_sender(Config.from_env({}))
    assert isinstance(sender, GuardedEmailSender)
    sender.store.suppress("ada@example.com")

    result = sender.send(
        "activation", "ada@example.com", {"app_name": "Taipan", "link": "https://x/y"}
    )

    assert result.status is SendStatus.SUPPRESSED
    assert isinstance(sender.inner, FakeEmailSender)
    assert sender.inner.list_sent() == []


def test_key_selects_guarded_resend_adapter() -> None:
    cfg = Config.from_env({"API_RESEND_API_KEY": "re_test_key"})

    sender = build_email_sender(cfg)

    assert isinstance(sender, GuardedEmailSender)
    assert isinstance(sender.inner, ResendEmailSender)


def test_from_address_reaches_payload() -> None:
    transport = StubTransport()
    cfg = Config.from_env(
        {"API_RESEND_API_KEY": "re_test_key", "API_MAIL_FROM": "noreply@example.com"}
    )

    sender = build_email_sender(cfg, transport=transport)
    result = sender.send(
        "activation", "ada@example.com", {"app_name": "Taipan", "link": "https://x/y"}
    )

    assert result.status is SendStatus.SENT
    [payload] = transport.calls
    assert payload["from"] == "noreply@example.com"
    assert payload["to"] == ["ada@example.com"]


def test_key_never_reaches_web_client(monkeypatch: pytest.MonkeyPatch) -> None:
    from api.main import app
    from fastapi.testclient import TestClient

    key = "re_live_secret_abc123"
    monkeypatch.setenv("API_RESEND_API_KEY", key)
    monkeypatch.delenv("API_AUTO_MIGRATE", raising=False)
    with TestClient(app) as client:
        root = client.get("/")
        schema = client.get("/openapi.json")

    assert root.status_code == 200
    assert schema.status_code == 200
    assert key not in root.text
    assert key not in schema.text
