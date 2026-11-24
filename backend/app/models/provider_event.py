import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum,
    String,
    ForeignKey,
    Text,
    JSON,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base
from app.models.enums import ProviderEventStatus


class ProviderEvent(Base):
    __tablename__ = "provider_events"

    __table_args__ = (
        UniqueConstraint(
            "provider_name",
            "provider_event_id",
            name="uq_provider_event_identity"
        ),
        Index(
            "ix_provider_events_call_status",
            "call_id",
            "processing_status"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )

    call_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("calls.id"),
        nullable=False,
        index=True
    )

    provider_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    provider_event_id: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    processing_status: Mapped[ProviderEventStatus] = mapped_column(
        Enum(
            ProviderEventStatus,
            name="provider_event_status",
            native_enum=False
        ),
        default=ProviderEventStatus.RECEIVED,
        nullable=False
    )

    payload: Mapped[dict] = mapped_column(
        JSON,
        nullable=False
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    def __repr__(self):
        return (
            f"<ProviderEvent(id={self.id}, "
            f"event={self.event_type}, "
            f"status={self.processing_status.value})>"
        )