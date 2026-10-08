"""Thin change route: shape check, error map, session policy, notice."""

from typing import Annotated

from email_delivery import EmailSender
from fastapi import APIRouter, Depends, HTTPException, Response

from api import auth_flow, authz, password_change, sessions
from api.db import DbSession
from api.mail import get_email_sender
from api.password_change.notice import send_change_notice
from api.schemas import PasswordChangeIn, PasswordChangeOut

router = APIRouter(prefix="/account", tags=["account"])


@router.post("/password", response_model=PasswordChangeOut)
def change_password(
    payload: PasswordChangeIn,
    response: Response,
    principal: Annotated[authz.Principal, Depends(authz.current_principal)],
    db: DbSession,
    sender: Annotated[EmailSender, Depends(get_email_sender)],
) -> PasswordChangeOut:
    if payload.new_password != payload.confirm_new_password:
        raise HTTPException(status_code=422, detail="new passwords do not match")
    try:
        password_change.change(
            db, principal.user_id, payload.current_password, payload.new_password
        )
    except password_change.WrongCurrentPassword as exc:
        raise HTTPException(status_code=401, detail="wrong current password") from exc
    except password_change.WeakPassword as exc:
        raise HTTPException(status_code=422, detail="weak password") from exc
    except password_change.SameAsOldPassword as exc:
        raise HTTPException(status_code=422, detail="new password matches current") from exc
    # REVOKE_OTHER_SESSIONS policy: kill every session, then re-mint for
    # this device, so the caller stays signed in and other devices do not.
    if password_change.REVOKE_OTHER_SESSIONS:
        sessions.revoke_all(principal.user_id)
        sessions.set_session_cookie(response, auth_flow.issue(db, principal.user_id))
    send_change_notice(sender, principal.email)
    return PasswordChangeOut(other_devices_signed_out=password_change.REVOKE_OTHER_SESSIONS)
