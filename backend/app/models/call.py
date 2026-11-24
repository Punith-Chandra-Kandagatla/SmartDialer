import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum,
    String,
    ForeignKey,
    Index,
    Integer,
    CheckConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base
from app.models.enums import CallStatus


ACTIVE_CALL_STATUSES = (
    "'RESERVED', 'INITIATED', 'RINGING', 'ANSWERED', 'CONNECTED'"
)


class Call(Base):
    __tablename__ = "calls"

    __table_args__ = (
        CheckConstraint(
            "attempt_number > 0",
            name="ck_call_attempt_number"
        ),

        Index(
            "ix_calls_campaign_status",
            "campaign_id",
            "status"
        ),

        Index(
            "ix_calls_agent_status",
            "agent_id",
            "status"
        ),

        Index(
            "ix_calls_borrower_status",
            "borrower_id",
            "status"
        ),

        Index(
            "uq_calls_active_agent",
            "agent_id",
            unique=True,
            postgresql_where=text(
                f"agent_id IS NOT NULL AND status IN ({ACTIVE_CALL_STATUSES})"
            )
        ),

        Index(
            "uq_calls_active_borrower",
            "borrower_id",
            unique=True,
            postgresql_where=text(
                f"status IN ({ACTIVE_CALL_STATUSES})"
            )
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        nullable=False
    )

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id"),
        nullable=False,
        index=True
    )

    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id"),
        nullable=True,
        index=True
    )

    borrower_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("borrowers.id"),
        nullable=False,
        index=True
    )

    # Identifies the reservation shared by the agent and borrower
    reservation_token: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True
    )

    provider_name: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    provider_call_id: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        unique=True
    )

    status: Mapped[CallStatus] = mapped_column(
        Enum(
            CallStatus,
            name="call_status",
            native_enum=False
        ),
        default=CallStatus.QUEUED,
        nullable=False
    )

    attempt_number: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False
    )

    reserved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    initiated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    answered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    failure_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
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
            f"<Call(id={self.id}, "
            f"status={self.status.value}, "
            f"provider={self.provider_name})>"
        )