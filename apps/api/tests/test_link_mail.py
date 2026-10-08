"""Link mail module contract: one app name, one link builder, best effort."""

import logging

from api.config import DEFAULT_APP_BASE_URL
from api.link_mail import MailLink, send_link, send_notice
from email_delivery import FakeEmailSender
from email_delivery.templates import ACTIVATION, PASSWORD_CHANGE, RESET

RECIPIENT = "ada@example.com"
TOKEN = "raw-token-123"


class RaisingSender:
    """Send always explodes; best effort must swallow it."""

    def __init__(self) -> None:
        self.calls = 0

    def send(self, template: str, recipient: str, data: dict) -> object:
        self.calls += 1
        raise RuntimeError("smtp down")


def test_link_mail_sends_once_with_built_link_and_rendered_data() -> None:
    sender = FakeEmailSender()

    send_link(sender, ACTIVATION, RECIPIENT, MailLink(path="/register", query={"token": TOKEN}))

    [mail] = sender.list_sent()
    assert mail.template == ACTIVATION
    assert mail.recipient == RECIPIENT
    # Full equality: default origin, path, urlencoded query, raw token.
    assert mail.data["link"] == f"{DEFAULT_APP_BASE_URL}/register?token={TOKEN}"
    assert mail.data["app_name"] == "Taipan"
    # Rendered fields prove the send went through the seam's rendered_send.
    assert mail.data["subject"] == "Activate your Taipan account"
    assert "Hello from Taipan." in mail.data["body"]
    assert mail.data["link"] in mail.data["body"]


def test_notice_mail_sends_app_name_without_link() -> None:
    sender = FakeEmailSender()

    send_notice(sender, PASSWORD_CHANGE, RECIPIENT)

    [mail] = sender.list_sent()
    assert mail.data["app_name"] == "Taipan"
    assert "link" not in mail.data
    assert mail.data["subject"] == "Your Taipan password was changed"


def test_raising_sender_link_returns_none_and_logs_one_warning(caplog) -> None:
    sender = RaisingSender()

    with caplog.at_level(logging.WARNING, logger="api.link_mail"):
        result = send_link(
            sender, RESET, RECIPIENT, MailLink(path="/reset", query={"token": TOKEN})
        )

    assert result is None
    assert sender.calls == 1
    # Exactly one warning from the module, with the stable on-call shape.
    assert [
        r.getMessage()
        for r in caplog.records
        if r.name == "api.link_mail" and r.levelname == "WARNING"
    ] == [f"mail send failed template={RESET} recipient={RECIPIENT} error=smtp down"]


def test_raising_sender_notice_returns_none_and_logs_one_warning(caplog) -> None:
    sender = RaisingSender()

    with caplog.at_level(logging.WARNING, logger="api.link_mail"):
        result = send_notice(sender, PASSWORD_CHANGE, RECIPIENT)

    assert result is None
    assert sender.calls == 1
    assert [
        r.getMessage()
        for r in caplog.records
        if r.name == "api.link_mail" and r.levelname == "WARNING"
    ] == [f"mail send failed template={PASSWORD_CHANGE} recipient={RECIPIENT} error=smtp down"]


def test_base_url_override_changes_built_origin(monkeypatch) -> None:
    monkeypatch.setenv("API_APP_BASE_URL", "https://mail.example.com")
    sender = FakeEmailSender()

    send_link(sender, RESET, RECIPIENT, MailLink(path="/reset", query={"token": TOKEN}))

    [mail] = sender.list_sent()
    assert mail.data["link"] == f"https://mail.example.com/reset?token={TOKEN}"
