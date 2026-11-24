import uuid

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BorrowerStatus


class BorrowerCreate(BaseModel):
    external_ref: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=150)
    phone_number: str = Field(min_length=7, max_length=20)
    max_attempts: int = Field(default=3, ge=1, le=10)


class BorrowerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    external_ref: str
    name: str
    phone_number: str
    status: BorrowerStatus
    attempt_count: int
    max_attempts: int
    is_active: bool
    next_eligible_at: datetime | None
    created_at: datetime
    updated_at: datetime