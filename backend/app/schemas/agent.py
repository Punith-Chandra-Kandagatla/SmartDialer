import uuid

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.enums import AgentStatus


class AgentCreate(BaseModel):
    name: str
    email: EmailStr


class AgentStatusUpdate(BaseModel):
    status: AgentStatus


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    status: AgentStatus
    last_heartbeat: datetime | None
    created_at: datetime
    updated_at: datetime