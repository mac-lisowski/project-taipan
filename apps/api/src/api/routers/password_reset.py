"""Thin reset routes: body map, error map, cookie set. No token rules here."""

from typing import Annotated

from email_delivery import EmailSender
from fastapi import APIRouter, Depends, HTTPException, Response

from api import password_reset, sessions, tokens, users
from api.db import DbSession
from api.mail import get_email_sender
from api.schemas import ForgotIn, ResetIn

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/forgot", status_code=204)
def forgot(
    payload: ForgotIn,
    db: DbSession,
    sender: Annotated[EmailSender, Depends(get_email_sender)],
) -> None:
    password_reset.request(db, email=payload.email, sender=sender)


@router.post("/reset", status_code=204)
def reset(payload: ResetIn, response: Response, db: DbSession) -> None:
    try:
        token = password_reset.reset(db, token=payload.token, new_password=payload.new_password)
    except tokens.TokenError as exc:
        raise HTTPException(status_code=400, detail="invalid or expired reset link") from exc
    except users.NotFound as exc:
        # The user row can vanish while a link lives; a dead link stays dead.
        raise HTTPException(status_code=400, detail="invalid or expired reset link") from exc
    except password_reset.WeakPassword as exc:
        raise HTTPException(status_code=422, detail="weak password") from exc
    sessions.set_session_cookie(response, token)
