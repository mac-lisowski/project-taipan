"""Resend bounce webhook intake. Verifies with the official SDK."""

from __future__ import annotations

from typing import Any, cast

import resend
from email_delivery import (
    DEFAULT_BOUNCE_SUBTYPE,
    GuardedEmailSender,
    bounce_kind_for,
)
from fastapi import APIRouter, HTTPException, Request

from api.config import get_config
from api.mail import get_email_sender

router = APIRouter(prefix="/email/webhooks", tags=["email"])


def _recipient(data: Any) -> str:
    """First address from the event payload; empty when none is present."""
    if not isinstance(data, dict):
        return ""
    to = data.get("to", data.get("email", data.get("recipient", "")))
    if isinstance(to, list):
        to = to[0] if to else ""
    return to.strip() if isinstance(to, str) else ""


@router.post("/resend")
async def resend_webhook(request: Request) -> dict[str, Any]:
    """Record one provider bounce report. Unknown kinds stay ignored."""
    body = await request.body()
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="malformed webhook body") from exc
    try:
        event = resend.Webhooks.verify(
            {
                "payload": text,
                "headers": {
                    "id": request.headers.get("svix-id", ""),
                    "timestamp": request.headers.get("svix-timestamp", ""),
                    "signature": request.headers.get("svix-signature", ""),
                },
                "webhook_secret": get_config().mail.resend_webhook_secret,
            }
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="invalid webhook signature") from exc
    if not isinstance(event, dict):
        raise HTTPException(status_code=400, detail="malformed webhook body")
    data = event.get("data", {})
    event_type = event.get("type", "")
    bounce = data.get("bounce", {}) if isinstance(data, dict) else {}
    subtype = (
        bounce.get("type", DEFAULT_BOUNCE_SUBTYPE)
        if isinstance(bounce, dict)
        else DEFAULT_BOUNCE_SUBTYPE
    )
    kind = bounce_kind_for(event_type, subtype)
    if kind is None:
        return {"status": "ignored"}
    address = _recipient(data)
    if not address:
        return {"status": "ignored"}
    # The composition root always installs the guard; the cast states that.
    sender = cast(GuardedEmailSender, get_email_sender(request))
    # Svix retries share the message id, so the header is the dedupe key.
    suppressed = sender.record_bounce(address, kind, event_id=request.headers.get("svix-id"))
    return {"status": "recorded", "suppressed": suppressed}
