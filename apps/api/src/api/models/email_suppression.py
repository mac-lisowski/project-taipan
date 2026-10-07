from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base


class EmailSuppression(Base):
    """Do-not-send set. Keyed by address; mirrors the migration exactly."""

    __tablename__ = "email_suppressions"
    __table_args__ = (
        CheckConstraint(
            "reason IN ('hard', 'soft-limit', 'complaint')",
            name="ck_email_suppressions_reason",
        ),
    )

    address: Mapped[str] = mapped_column(Text, primary_key=True)
    reason: Mapped[str] = mapped_column(Text)
    soft_bounces: Mapped[int] = mapped_column(Integer, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EmailSendCounter(Base):
    """Lifetime send counts per recipient and template."""

    __tablename__ = "email_send_counters"

    recipient: Mapped[str] = mapped_column(Text, primary_key=True)
    template: Mapped[str] = mapped_column(Text, primary_key=True)
    sent_count: Mapped[int] = mapped_column(BigInteger, server_default="0")


class EmailWebhookEvent(Base):
    """Seen provider event ids for replay dedupe."""

    __tablename__ = "email_webhook_events"

    event_id: Mapped[str] = mapped_column(Text, primary_key=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
