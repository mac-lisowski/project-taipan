"""Sender seam tests via the fake adapter."""

from email_delivery import FakeEmailSender, SendResult, SendStatus


def test_send_captures_template_recipient_and_data() -> None:
    sender = FakeEmailSender()

    result = sender.send("activation", "ada@example.com", {"name": "Ada", "link": "https://x/y"})

    assert result.status is SendStatus.SENT
    [mail] = sender.list_sent()
    assert mail.template == "activation"
    assert mail.recipient == "ada@example.com"
    assert mail.data == {"name": "Ada", "link": "https://x/y"}


def test_clear_empties_the_store() -> None:
    sender = FakeEmailSender()
    sender.send("activation", "ada@example.com", {})

    sender.clear()

    assert sender.list_sent() == []


def test_result_type_covers_all_outcomes() -> None:
    assert len({SendStatus.SENT, SendStatus.SUPPRESSED, SendStatus.FAILED}) == 3
    assert SendResult(status=SendStatus.SENT).status is SendStatus.SENT
    assert (
        SendResult(status=SendStatus.SUPPRESSED, reason="hard-bounce").status
        is SendStatus.SUPPRESSED
    )
    assert SendResult(status=SendStatus.FAILED, reason="no-key").status is SendStatus.FAILED
