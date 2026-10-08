"""Resend adapter tests. Stubbed transport only, never the real vendor."""

from email_delivery.resend import ResendEmailSender
from email_delivery.sender import SendStatus


class StubTransport:
    """Records payloads, returns canned outcomes. No network."""

    def __init__(self, outcome: str = "ok") -> None:
        self.outcome = outcome
        self.calls: list[dict] = []

    def post_email(self, payload: dict) -> None:
        self.calls.append(payload)
        if self.outcome != "ok":
            from email_delivery.resend import ResendError

            raise ResendError(self.outcome)


def test_sdk_send_uses_configured_key_and_params(monkeypatch) -> None:
    import resend

    calls: list[dict] = []

    def fake_send(params: dict):
        calls.append(params)
        return {"id": "email-id-1"}

    monkeypatch.setattr("resend.Emails.send", fake_send)
    monkeypatch.setattr("resend.api_key", None)
    sender = ResendEmailSender(api_key="re_live_key", from_address="noreply@example.com")

    result = sender.send(
        "activation",
        "ada@example.com",
        {"app_name": "Taipan", "link": "https://x/y"},
    )

    assert result.status is SendStatus.SENT
    assert resend.api_key == "re_live_key"
    [params] = calls
    assert params["from"] == "noreply@example.com"
    assert params["to"] == ["ada@example.com"]
    assert "Activate your Taipan account" in params["subject"]


def test_no_key_fails_closed_without_network() -> None:
    transport = StubTransport()
    sender = ResendEmailSender.from_config(
        api_key="", from_address="noreply@example.com", transport=transport
    )

    result = sender.send("activation", "ada@example.com", {"link": "https://x/y"})

    assert result.status is SendStatus.FAILED
    assert result.reason == "no-key"
    assert transport.calls == []


def test_missing_key_fails_closed_without_network() -> None:
    transport = StubTransport()
    sender = ResendEmailSender.from_config(
        api_key=None, from_address="noreply@example.com", transport=transport
    )

    result = sender.send("activation", "ada@example.com", {})

    assert result.status is SendStatus.FAILED
    assert result.reason == "no-key"
    assert transport.calls == []


def test_transport_failure_maps_to_failed() -> None:
    transport = StubTransport(outcome="resend-500")
    sender = ResendEmailSender(
        api_key="re_test_key", from_address="noreply@example.com", transport=transport
    )

    result = sender.send(
        "activation",
        "ada@example.com",
        {"app_name": "Taipan", "link": "https://x/y"},
    )

    assert result.status is SendStatus.FAILED
    assert result.reason == "resend-500"
    assert "re_test_key" not in result.reason


def test_sdk_failure_maps_to_stable_reason(monkeypatch) -> None:
    def boom(params: dict):
        raise RuntimeError("vendor says no")

    monkeypatch.setattr("resend.Emails.send", boom)
    monkeypatch.setattr("resend.api_key", None)
    sender = ResendEmailSender(api_key="re_test_key", from_address="noreply@example.com")

    result = sender.send(
        "activation",
        "ada@example.com",
        {"app_name": "Taipan", "link": "https://x/y"},
    )

    assert result.status is SendStatus.FAILED
    assert result.reason == "resend-send-failed"
    assert "vendor says no" not in result.reason


def test_no_secrets_reach_logs(caplog) -> None:
    key = "re_secret_key_abc123"
    token_link = "https://x/activate?t=token-secret-xyz"
    transport = StubTransport(outcome="boom")
    sender = ResendEmailSender(api_key=key, from_address="noreply@example.com", transport=transport)

    with caplog.at_level("WARNING", logger="email_delivery.resend"):
        result = sender.send(
            "activation",
            "ada@example.com",
            {"app_name": "Taipan", "link": token_link},
        )

    assert result.status is SendStatus.FAILED
    assert key not in result.reason
    assert token_link not in result.reason
    logged = "\n".join(f"{r.levelname} {r.getMessage()}" for r in caplog.records)
    assert key not in logged
    assert token_link not in logged
    assert "activation" in logged


def test_stubbed_transport_success_maps_to_sent() -> None:
    transport = StubTransport()
    sender = ResendEmailSender(
        api_key="re_test_key", from_address="noreply@example.com", transport=transport
    )

    result = sender.send(
        "activation",
        "ada@example.com",
        {"app_name": "Taipan", "link": "https://x/y"},
    )

    assert result.status is SendStatus.SENT
    [payload] = transport.calls
    assert payload["from"] == "noreply@example.com"
    assert payload["to"] == ["ada@example.com"]
    assert payload["subject"] == "Activate your Taipan account"
    assert "https://x/y" in payload["text"]


def test_bad_template_data_rejects_without_network() -> None:
    transport = StubTransport()
    sender = ResendEmailSender(
        api_key="re_test_key", from_address="noreply@example.com", transport=transport
    )

    result = sender.send("activation", "ada@example.com", {"link": "https://x/y"})

    assert result.status is SendStatus.FAILED
    assert transport.calls == []
