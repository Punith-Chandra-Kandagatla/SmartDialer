import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum,
    Integer,
    String,
    Boolean,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base
from app.models.enums import BorrowerStatus


class Borrower(Base):
    __tablename__ = "borrowers"

    __table_args__ = (
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_borrower_attempt_count"
        ),

        CheckConstraint(
            "max_attempts > 0",
            name="ck_borrower_max_attempts"
        ),

        CheckConstraint(
            """
            (reservation_token IS NULL AND reserved_until IS NULL)
            OR
            (reservation_token IS NOT NULL AND reserved_until IS NOT NULL)
            """,
            name="ck_borrower_reservation_fields"
        ),

        UniqueConstraint(
            "reservation_token",
            name="uq_borrower_reservation_token"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )

    external_ref: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    phone_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )

    status: Mapped[BorrowerStatus] = mapped_column(
        Enum(
            BorrowerStatus,
            name="borrower_status",
            native_enum=False
        ),
        default=BorrowerStatus.ELIGIBLE,
        nullable=False
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    max_attempts: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False
    )

    reservation_token: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True
    )

    reserved_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    next_eligible_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
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
            f"<Borrower(id={self.id}, "
            f"name={self.name}, "
            f"status={self.status.value})>"
        )