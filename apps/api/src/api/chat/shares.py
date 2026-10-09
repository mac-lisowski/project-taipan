"""Share snapshots: deterministic HMAC tokens, frozen JSONB, owner checks."""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from api.chat import threads
from api.config import get_config
from api.models import ChatThread, ChatThreadShare

__all__ = ["NotFound", "create_or_refresh", "is_shared", "read_snapshot", "revoke"]

logger = logging.getLogger(__name__)

# Per-process fallback when API_SHARE_TOKEN_SECRET is unset. A random
# default inside Config.from_env would break its equality pin; prod must
# set a stable value or restart rewrites every live share's hash.
_fallback_secret: bytes | None = None

# The partial unique index predicate; ON CONFLICT matching must repeat it.
_LIVE_PREDICATE = text("revoked_at IS NULL")


class NotFound(Exception):
    """No live share answers this address: unknown, revoked, or expired."""


def _secret() -> bytes:
    configured = get_config().chat.share_token_secret
    if configured:
        return configured.encode()
    global _fallback_secret
    if _fallback_secret is None:
        _fallback_secret = secrets.token_bytes(32)
        # Loud once per process: an unset secret means share links die on
        # restart and disagree across replicas.
        logger.warning(
            "API_SHARE_TOKEN_SECRET is unset; share links are bound to this "
            "process and break across restarts and replicas"
        )
    return _fallback_secret


def _token_for(share_id: UUID) -> str:
    # Deterministic: the same row always yields the same URL, so the SDK
    # re-calling create on every modal open returns the existing link.
    digest = hmac.new(_secret(), share_id.bytes, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _unrevoked_share(session: Session, thread_id: UUID) -> ChatThreadShare | None:
    """The row holding the thread's live-share slot, expired or not."""
    return session.scalar(
        select(ChatThreadShare).where(
            ChatThreadShare.thread_id == thread_id,
            ChatThreadShare.revoked_at.is_(None),
        )
    )


def _expired(share: ChatThreadShare) -> bool:
    # One clock for every liveness check: read_snapshot binds the same
    # Python-side now(), so a share near its boundary cannot read live on
    # one path and dead on the other.
    return share.expires_at is not None and share.expires_at <= datetime.now(UTC)


def _owned_thread(session: Session, user_id: int, tenant_id: str, thread_id: UUID) -> ChatThread:
    # Hides other tenants' threads behind the same 404 as other users';
    # a mismatch would otherwise 500 in the tenant flush guard.
    thread = threads.get(session, user_id, thread_id)
    if thread.tenant_id != tenant_id:
        raise threads.NotFound(thread_id)
    return thread


def _snapshot(thread: ChatThread) -> list[dict]:
    """Project to the public shape: system prompts and extra keys never leave."""
    return [
        {"role": row.role, "content": row.content.get("content")}
        for row in thread.messages
        if row.role != "system"
    ]


def create_or_refresh(
    session: Session, user_id: int, tenant_id: str, thread_id: UUID
) -> tuple[ChatThreadShare, str]:
    """Return the live share and its URL token, creating or refreshing it."""
    thread = _owned_thread(session, user_id, tenant_id, thread_id)
    share = _unrevoked_share(session, thread_id)
    if share is not None and _expired(share):
        # An expired row still holds the slot; retire it for audit and
        # mint a fresh row so the caller gets a live token, not a 404.
        share.revoked_at = func.now()
        session.flush()
        share = None
    if share is None:
        share_id = uuid4()
        snapshot = _snapshot(thread)
        # A flush IntegrityError deactivates the session (a savepoint cannot
        # recover it), so ON CONFLICT scoped to the live-share index absorbs the race.
        session.execute(
            insert(ChatThreadShare)
            .values(
                # The id mints client-side so the HMAC token is computable
                # before the row exists.
                id=share_id,
                token_hash=_hash(_token_for(share_id)),
                thread_id=thread_id,
                tenant_id=tenant_id,
                snapshot=snapshot,
                title=thread.title,
                created_by_user_id=user_id,
            )
            .on_conflict_do_nothing(index_elements=["thread_id"], index_where=_LIVE_PREDICATE)
        )
        share = _unrevoked_share(session, thread_id)
        if share is None:
            # A suppressed conflict implies an unrevoked winner exists.
            raise RuntimeError("share insert lost the race but no winner exists")
        if share.id != share_id:
            # Lost the race: the winner's row gets the snapshot refresh.
            share.snapshot = snapshot
            share.title = thread.title
    else:
        share.snapshot = _snapshot(thread)
        share.title = thread.title
    token = _token_for(share.id)
    digest = _hash(token)
    if share.token_hash != digest:
        # Secret rotated (or the per-process fallback changed): overwrite
        # the stored hash instead of silently serving a dead URL.
        share.token_hash = digest
    session.flush()
    return share, token


def is_shared(session: Session, user_id: int, tenant_id: str, thread_id: UUID) -> bool:
    """Whether a live (unrevoked, unexpired) share exists for the thread."""
    _owned_thread(session, user_id, tenant_id, thread_id)
    share = _unrevoked_share(session, thread_id)
    return share is not None and not _expired(share)


def revoke(session: Session, user_id: int, tenant_id: str, thread_id: UUID) -> None:
    _owned_thread(session, user_id, tenant_id, thread_id)
    share = _unrevoked_share(session, thread_id)
    if share is None:
        raise NotFound(thread_id)
    share.revoked_at = func.now()
    session.flush()


def read_snapshot(session: Session, token: str) -> ChatThreadShare:
    share = session.scalar(
        select(ChatThreadShare).where(
            ChatThreadShare.token_hash == _hash(token),
            ChatThreadShare.revoked_at.is_(None),
            or_(
                ChatThreadShare.expires_at.is_(None),
                ChatThreadShare.expires_at > datetime.now(UTC),
            ),
        )
    )
    if share is None:
        raise NotFound(token)
    return share
