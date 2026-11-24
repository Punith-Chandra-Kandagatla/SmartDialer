import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum,
    String,
    Integer,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base
from app.models.enums import AgentStatus


class Agent(Base):
    __tablename__ = "agents"

    __table_args__ = (
        CheckConstraint(
            """
            (reservation_token IS NULL AND reserved_until IS NULL)
            OR
            (reservation_token IS NOT NULL AND reserved_until IS NOT NULL)
            """,
            name="ck_agent_reservation_fields"
        ),

        UniqueConstraint(
            "reservation_token",
            name="uq_agent_reservation_token"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        nullable=False,
        index=True
    )

    status: Mapped[AgentStatus] = mapped_column(
        Enum(
            AgentStatus,
            name="agent_status",
            native_enum=False
        ),
        default=AgentStatus.OFFLINE,
        nullable=False
    )

    reservation_token: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True
    )

    reserved_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    last_heartbeat: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
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

    __mapper_args__ = {
        "version_id_col": version
    }

    def __repr__(self):
        return (
            f"<Agent(id={self.id}, "
            f"name={self.name}, "
            f"status={self.status.value})>"
        )