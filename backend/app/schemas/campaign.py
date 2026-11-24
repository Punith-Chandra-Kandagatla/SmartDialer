from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    CampaignStatus,
    DialingMode,
)


class CampaignCreate(BaseModel):

    name: str = Field(
        min_length=3,
        max_length=150,
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
    )

    dialing_mode: DialingMode = DialingMode.PROGRESSIVE

    max_concurrent_calls: int = Field(
        default=50,
        gt=0,
    )

    max_attempts_per_borrower: int = Field(
        default=3,
        gt=0,
    )

    target_answer_rate: float = Field(
        default=0.40,
        ge=0,
        le=1,
    )

    max_abandoned_rate: float = Field(
        default=0.03,
        ge=0,
        le=1,
    )


class CampaignUpdate(BaseModel):

    name: str | None = Field(
        default=None,
        min_length=3,
        max_length=150,
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
    )

    max_concurrent_calls: int | None = Field(
        default=None,
        gt=0,
    )

    max_attempts_per_borrower: int | None = Field(
        default=None,
        gt=0,
    )

    target_answer_rate: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )

    max_abandoned_rate: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )


class CampaignResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None

    dialing_mode: DialingMode
    status: CampaignStatus

    max_concurrent_calls: int
    max_attempts_per_borrower: int

    target_answer_rate: float
    max_abandoned_rate: float

    created_at: datetime
    updated_at: datetime