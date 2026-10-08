"""Jinja2 render step: typed data, validated before any send."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from email_delivery.sender import EmailSender, SendResult

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"

ACTIVATION = "activation"
RESET = "reset"
PASSWORD_CHANGE = "password_change"

_SUBJECTS = {
    ACTIVATION: "Activate your {app_name} account",
    RESET: "Reset your {app_name} access",
    PASSWORD_CHANGE: "Your {app_name} password was changed",
}

# Fields each template needs; link only where the mail carries a URL.
_REQUIRED = {
    ACTIVATION: ("app_name", "link"),
    RESET: ("app_name", "link"),
    PASSWORD_CHANGE: ("app_name",),
}


class TemplateValidationError(ValueError):
    """Bad template name or data. Raised before any network use."""


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    body: str


@dataclass(frozen=True)
class _TemplateData:
    app_name: str
    link: str | None


_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=False,
    undefined=StrictUndefined,
)


def _validated(data: Mapping[str, Any], required: tuple[str, ...]) -> _TemplateData:
    try:
        app_name = data["app_name"]
        link = data["link"] if "link" in required else None
    except KeyError as exc:
        raise TemplateValidationError(f"missing field: {exc.args[0]}") from exc
    if not isinstance(app_name, str) or not app_name.strip():
        raise TemplateValidationError("app_name must be a non-empty string")
    if "link" in required and (
        not isinstance(link, str) or not link.startswith(("https://", "http://"))
    ):
        raise TemplateValidationError("link must be an http(s) URL")
    return _TemplateData(app_name=app_name.strip(), link=link)


def render(template: str, data: Mapping[str, Any]) -> RenderedEmail:
    """Render subject and body. Rejects bad input before any send."""
    if template not in _SUBJECTS:
        raise TemplateValidationError(f"unknown template: {template}")
    typed = _validated(data, _REQUIRED[template])
    body = _env.get_template(f"{template}.j2").render(app_name=typed.app_name, link=typed.link)
    return RenderedEmail(
        subject=_SUBJECTS[template].format(app_name=typed.app_name),
        body=body,
    )


def rendered_send(
    sender: EmailSender,
    template: str,
    recipient: str,
    data: Mapping[str, Any],
) -> SendResult:
    """Validate, render, then send. The sender captures subject and body."""
    rendered = render(template, data)
    enriched = {**dict(data), "subject": rendered.subject, "body": rendered.body}
    return sender.send(template, recipient, enriched)
