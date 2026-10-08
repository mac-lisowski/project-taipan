"""Thin registration routes: body map, error map, cookie set. No token rules here."""

from typing import Annotated

from email_delivery import EmailSender
from fastapi import APIRouter, Depends, HTTPException, Response

from api import registration, sessions, tokens
from api.db import DbSession
from api.mail import get_email_sender
from api.schemas import ActivateIn, RegisterIn

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=204)
def register(
    payload: RegisterIn,
    db: DbSession,
    sender: Annotated[EmailSender, Depends(get_email_sender)],
) -> None:
    try:
        registration.request(db, email=payload.email, sender=sender)
    except registration.RegistrationClosed as exc:
        # A closed platform shows no sign up door, not even an error page shape.
        raise HTTPException(status_code=404, detail="Not Found") from exc


@router.post("/activate", status_code=204)
def activate(payload: ActivateIn, response: Response, db: DbSession) -> None:
    try:
        token = registration.activate(db, token=payload.token, new_password=payload.password)
    except tokens.TokenError as exc:
        raise HTTPException(status_code=400, detail="invalid or expired activation link") from exc
    except registration.WeakPassword as exc:
        raise HTTPException(status_code=422, detail="weak password") from exc
    sessions.set_session_cookie(response, token)
