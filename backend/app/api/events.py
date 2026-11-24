from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.event_processor import EventProcessor


router = APIRouter(
    prefix="/api/v1/providers",
    tags=["Provider Events"]
)


class ProviderEventRequest(BaseModel):
    provider_event_id: str = Field(min_length=1)
    provider_call_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)


@router.post("/{provider_name}/events")
def receive_provider_event(
    provider_name: str,
    data: ProviderEventRequest,
    db: Session = Depends(get_db),
):
    try:
        result = EventProcessor.process_event(
            db=db,
            provider_name=provider_name,
            provider_event_id=data.provider_event_id,
            provider_call_id=data.provider_call_id,
            event_type=data.event_type,
            payload=data.payload,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result,
            )

        return result

    except HTTPException:
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to process provider event",
        )