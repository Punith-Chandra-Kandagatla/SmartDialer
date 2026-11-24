import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum,
    String,
    Integer,
    Float,
    Text,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base
from app.models.enums import CampaignStatus, DialingMode


class Campaign(Base):
    __tablename__ = "campaigns"

    __table_args__ = (
        CheckConstraint(
            "max_concurrent_calls > 0",
            name="ck_campaign_max_concurrent_calls"
        ),
        CheckConstraint(
            "max_attempts_per_borrower > 0",
            name="ck_campaign_max_attempts"
        ),
        CheckConstraint(
            "target_answer_rate >= 0 AND target_answer_rate <= 1",
            name="ck_campaign_answer_rate"
        ),
        CheckConstraint(
            "max_abandoned_rate >= 0 AND max_abandoned_rate <= 1",
            name="ck_campaign_abandoned_rate"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    dialing_mode: Mapped[DialingMode] = mapped_column(
        Enum(
            DialingMode,
            name="dialing_mode",
            native_enum=False
        ),
        default=DialingMode.PROGRESSIVE,
        nullable=False
    )

    status: Mapped[CampaignStatus] = mapped_column(
        Enum(
            CampaignStatus,
            name="campaign_status",
            native_enum=False
        ),
        default=CampaignStatus.DRAFT,
        nullable=False
    )

    max_concurrent_calls: Mapped[int] = mapped_column(
        Integer,
        default=50,
        nullable=False
    )

    max_attempts_per_borrower: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False
    )

    target_answer_rate: Mapped[float] = mapped_column(
        Float,
        default=0.40,
        nullable=False
    )

    max_abandoned_rate: Mapped[float] = mapped_column(
        Float,
        default=0.03,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def __repr__(self):
        return (
            f"<Campaign(id={self.id}, "
            f"name={self.name}, "
            f"mode={self.dialing_mode.value}, "
            f"status={self.status.value})>"
        )
    