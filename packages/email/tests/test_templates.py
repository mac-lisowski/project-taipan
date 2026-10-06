"""Jinja2 template rendering for activation and reset mail."""

import pytest
from email_delivery import FakeEmailSender, SendStatus
from email_delivery.templates import (
    TemplateValidationError,
    render,
    rendered_send,
)


def test_activation_renders_subject_body_and_link() -> None:
    rendered = render(
        "activation",
        {"app_name": "Taipan", "link": "https://app.example/activate/abc"},
    )

    assert rendered.subject == "Activate your Taipan account"
    assert "Taipan" in rendered.body
    assert "https://app.example/activate/abc" in rendered.body


def test_reset_renders_subject_body_and_link() -> None:
    rendered = render(
        "reset",
        {"app_name": "Taipan", "link": "https://app.example/reset/xyz"},
    )

    assert rendered.subject == "Reset your Taipan access"
    assert "Taipan" in rendered.body
    assert "https://app.example/reset/xyz" in rendered.body


def test_unknown_template_rejects() -> None:
    with pytest.raises(TemplateValidationError):
        render("login", {"app_name": "Taipan", "link": "https://app.example/x"})


def test_missing_data_rejects_before_send() -> None:
    sender = FakeEmailSender()

    with pytest.raises(TemplateValidationError):
        rendered_send(sender, "activation", "ada@example.com", {"app_name": "Taipan"})

    assert sender.list_sent() == []


def test_bad_link_rejects_before_send() -> None:
    sender = FakeEmailSender()

    with pytest.raises(TemplateValidationError):
        rendered_send(
            sender,
            "reset",
            "ada@example.com",
            {"app_name": "Taipan", "link": "not-a-url"},
        )

    assert sender.list_sent() == []


def test_sender_path_captures_rendered_subject_body_and_link() -> None:
    sender = FakeEmailSender()

    result = rendered_send(
        sender,
        "activation",
        "ada@example.com",
        {"app_name": "Taipan", "link": "https://app.example/activate/abc"},
    )

    assert result.status is SendStatus.SENT
    [mail] = sender.list_sent()
    assert mail.template == "activation"
    assert mail.recipient == "ada@example.com"
    assert mail.data["subject"] == "Activate your Taipan account"
    assert "https://app.example/activate/abc" in mail.data["body"]


def test_rendered_output_carries_no_secret_material() -> None:
    rendered = render(
        "activation",
        {
            "app_name": "Taipan",
            "link": "https://app.example/activate/abc",
            "api_key": "re_test_secret",
        },
    )

    assert "re_test_secret" not in rendered.subject
    assert "re_test_secret" not in rendered.body
