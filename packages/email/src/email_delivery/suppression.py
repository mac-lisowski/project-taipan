"""Suppression, bounce stance, and send bounds around any sender."""

from collections.abc import Callable, Mapping
from enum import Enum
from typing import Any, Protocol

from email_delivery.sender import (
    EmailSender,
    SendResult,
    SendStatus,
)

MAX_SOFT_BOUNCES = 3
MAX_SENDS_PER_RECIPIENT = 100
MAX_SENDS_PER_RECIPIENT_TEMPLATE = 50

_SUPPRESSED_REASON = "suppressed"
_RECIPIENT_BOUND_REASON = "retry later: recipient bound"
_TEMPLATE_BOUND_REASON = "retry later: template bound"


class BounceKind(str, Enum):
    HARD = "hard"
    SOFT = "soft"
    COMPLAINT = "complaint"


def _key(address: str) -> str:
    return address.strip().lower()


class SuppressionStore(Protocol):
    """Port for suppression and send-rate state. Callers learn outcomes."""

    def is_suppressed(self, address: str) -> bool:
        """Check the do-not-send set. Case and whitespace insensitive."""
        ...

    def suppress(self, address: str, reason: str = "hard") -> None:
        """Add to the do-not-send set. Reason defaults to manual (hard)."""
        ...

    def record_bounce(self, address: str, kind: BounceKind, event_id: str | None = None) -> bool:
        """Fold one bounce report in. Repeat event ids are no-ops.

        Returns suppressed-now: True for HARD and COMPLAINT, and for
        SOFT once the count reaches MAX_SOFT_BOUNCES.
        """
        ...

    def send_allowed(self, template: str, recipient: str) -> str | None:
        """Pre-send gate. None means send; otherwise the reject reason."""
        ...

    def note_sent(self, template: str, recipient: str) -> None:
        """Count one SENT delivery, re-checking bounds inside."""
        ...


class MemorySuppressionStore:
    """In-memory port adapter for tests and local seams."""

    def __init__(self) -> None:
        self._suppressed: set[str] = set()
        self._soft_bounces: dict[str, int] = {}
        self._seen_events: set[str] = set()
        self._sent_counts: dict[str, int] = {}
        self._sent_template_counts: dict[tuple[str, str], int] = {}

    def is_suppressed(self, address: str) -> bool:
        return _key(address) in self._suppressed

    def suppress(self, address: str, reason: str = "hard") -> None:
        del reason
        self._suppressed.add(_key(address))

    def record_bounce(self, address: str, kind: BounceKind, event_id: str | None = None) -> bool:
        if event_id is not None:
            if event_id in self._seen_events:
                return self.is_suppressed(address)
            self._seen_events.add(event_id)
        if kind in (BounceKind.HARD, BounceKind.COMPLAINT):
            self.suppress(address)
            return True
        key = _key(address)
        count = self._soft_bounces.get(key, 0) + 1
        self._soft_bounces[key] = count
        if count >= MAX_SOFT_BOUNCES:
            self._suppressed.add(key)
        return self.is_suppressed(address)

    def send_allowed(self, template: str, recipient: str) -> str | None:
        key = _key(recipient)
        if key in self._suppressed:
            return _SUPPRESSED_REASON
        if self._sent_counts.get(key, 0) >= MAX_SENDS_PER_RECIPIENT:
            return _RECIPIENT_BOUND_REASON
        if self._sent_template_counts.get((key, template), 0) >= MAX_SENDS_PER_RECIPIENT_TEMPLATE:
            return _TEMPLATE_BOUND_REASON
        return None

    def note_sent(self, template: str, recipient: str) -> None:
        key = _key(recipient)
        template_key = (key, template)
        if self._sent_counts.get(key, 0) >= MAX_SENDS_PER_RECIPIENT:
            return
        if self._sent_template_counts.get(template_key, 0) >= MAX_SENDS_PER_RECIPIENT_TEMPLATE:
            return
        self._sent_counts[key] = self._sent_counts.get(key, 0) + 1
        self._sent_template_counts[template_key] = (
            self._sent_template_counts.get(template_key, 0) + 1
        )


# A soft-bounced row carries reason soft-limit before the count reaches
# the bound, so suppression reads reason plus count, never row presence.
_IS_SUPPRESSED_SQL = """
SELECT 1 FROM email_suppressions
WHERE address = :address
AND (reason IN ('hard', 'complaint') OR soft_bounces >= :soft_limit)
"""

_SUPPRESS_SQL = """
INSERT INTO email_suppressions (address, reason, soft_bounces)
VALUES (:address, :reason, 0)
ON CONFLICT (address) DO UPDATE
SET reason = EXCLUDED.reason, updated_at = now()
"""

_SOFT_BOUNCE_SQL = """
INSERT INTO email_suppressions (address, reason, soft_bounces)
VALUES (:address, 'soft-limit', 1)
ON CONFLICT (address) DO UPDATE SET
soft_bounces = email_suppressions.soft_bounces + 1,
reason = CASE
WHEN email_suppressions.reason IN ('hard', 'complaint')
THEN email_suppressions.reason
WHEN email_suppressions.soft_bounces + 1 >= :soft_limit THEN 'soft-limit'
ELSE email_suppressions.reason END,
updated_at = now()
RETURNING soft_bounces, reason
"""

_CLAIM_EVENT_SQL = """
INSERT INTO email_webhook_events (event_id) VALUES (:event_id)
ON CONFLICT DO NOTHING RETURNING event_id
"""

_SEND_STATE_SQL = """
SELECT
EXISTS(SELECT 1 FROM email_suppressions
WHERE address = :address
AND (reason IN ('hard', 'complaint') OR soft_bounces >= :soft_limit)) AS suppressed,
(SELECT COALESCE(SUM(sent_count), 0) FROM email_send_counters
WHERE recipient = :recipient) AS total,
COALESCE((SELECT sent_count FROM email_send_counters
WHERE recipient = :recipient AND template = :template), 0) AS template_count
"""

# One statement reads both bounds and writes, sharing one snapshot.
_NOTE_SENT_SQL = """
WITH state AS (
SELECT (SELECT COALESCE(SUM(sent_count), 0) FROM email_send_counters
WHERE recipient = :recipient) AS total,
COALESCE((SELECT sent_count FROM email_send_counters
WHERE recipient = :recipient AND template = :template), 0) AS template_count
)
INSERT INTO email_send_counters (recipient, template, sent_count)
SELECT :recipient, :template, 1 FROM state
WHERE total < :max_recipient AND template_count < :max_template
ON CONFLICT (recipient, template) DO UPDATE
SET sent_count = email_send_counters.sent_count + 1
"""


class PostgresSuppressionStore:
    """Postgres port adapter. Each method opens one short session.

    sqlalchemy stays a lazy import so this module keeps no hard
    database dependency; the adapter only runs where the app wires it.
    """

    def __init__(self, session_factory: Callable[[], Any]) -> None:
        self._sessions = session_factory

    def is_suppressed(self, address: str) -> bool:
        from sqlalchemy import text

        with self._sessions() as session:
            row = session.execute(
                text(_IS_SUPPRESSED_SQL),
                {"address": _key(address), "soft_limit": MAX_SOFT_BOUNCES},
            ).first()
            return row is not None

    def suppress(self, address: str, reason: str = "hard") -> None:
        from sqlalchemy import text

        with self._sessions() as session:
            session.execute(text(_SUPPRESS_SQL), {"address": _key(address), "reason": reason})
            session.commit()

    def record_bounce(self, address: str, kind: BounceKind, event_id: str | None = None) -> bool:
        from sqlalchemy import text

        key = _key(address)
        with self._sessions() as session:
            if event_id is not None:
                claimed = session.execute(text(_CLAIM_EVENT_SQL), {"event_id": event_id}).first()
                if claimed is None:
                    return self._is_suppressed_in(session, key)
            if kind in (BounceKind.HARD, BounceKind.COMPLAINT):
                reason = "hard" if kind == BounceKind.HARD else "complaint"
                session.execute(text(_SUPPRESS_SQL), {"address": key, "reason": reason})
                session.commit()
                return True
            row = session.execute(
                text(_SOFT_BOUNCE_SQL),
                {"address": key, "soft_limit": MAX_SOFT_BOUNCES},
            ).one()
            session.commit()
            count, reason = row.soft_bounces, row.reason
            return reason in ("hard", "complaint") or count >= MAX_SOFT_BOUNCES

    def _is_suppressed_in(self, session: Any, key: str) -> bool:
        from sqlalchemy import text

        row = session.execute(
            text(_IS_SUPPRESSED_SQL),
            {"address": key, "soft_limit": MAX_SOFT_BOUNCES},
        ).first()
        return row is not None

    def send_allowed(self, template: str, recipient: str) -> str | None:
        from sqlalchemy import text

        key = _key(recipient)
        with self._sessions() as session:
            state = (
                session.execute(
                    text(_SEND_STATE_SQL),
                    {
                        "address": key,
                        "recipient": key,
                        "template": template,
                        "soft_limit": MAX_SOFT_BOUNCES,
                    },
                )
                .one()
                ._mapping
            )
        if state["suppressed"]:
            return _SUPPRESSED_REASON
        if state["total"] >= MAX_SENDS_PER_RECIPIENT:
            return _RECIPIENT_BOUND_REASON
        if state["template_count"] >= MAX_SENDS_PER_RECIPIENT_TEMPLATE:
            return _TEMPLATE_BOUND_REASON
        return None

    def note_sent(self, template: str, recipient: str) -> None:
        from sqlalchemy import text

        key = _key(recipient)
        with self._sessions() as session:
            session.execute(
                text(_NOTE_SENT_SQL),
                {
                    "recipient": key,
                    "template": template,
                    "max_recipient": MAX_SENDS_PER_RECIPIENT,
                    "max_template": MAX_SENDS_PER_RECIPIENT_TEMPLATE,
                },
            )
            session.commit()


class GuardedEmailSender(EmailSender):
    """Checks suppression and bounds before delegating to the inner sender."""

    def __init__(self, inner: EmailSender, store: SuppressionStore) -> None:
        self._inner = inner
        self.store = store

    @property
    def inner(self) -> EmailSender:
        """The wrapped adapter. Tests pin adapter choice through this."""
        return self._inner

    def record_bounce(self, address: str, kind: BounceKind, event_id: str | None = None) -> bool:
        return self.store.record_bounce(address, kind, event_id=event_id)

    def send(self, template: str, recipient: str, data: Mapping[str, Any]) -> SendResult:
        reason = self.store.send_allowed(template, recipient)
        if reason is not None:
            status = SendStatus.SUPPRESSED if reason == _SUPPRESSED_REASON else SendStatus.FAILED
            return SendResult(status=status, reason=reason)
        result = self._inner.send(template, recipient, data)
        if result.status == SendStatus.SENT:
            self.store.note_sent(template, recipient)
        return result
