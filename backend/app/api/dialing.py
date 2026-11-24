import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.campaign import Campaign
from app.models.enums import DialingMode

from app.services.progressive_dialer import ProgressiveDialer
from app.services.call_execution_service import CallExecutionService

from app.providers.registry import provider_manager


router = APIRouter(
    prefix="/api/v1/dialer",
    tags=["Dialer Operations"]
)


class ProgressivePrepareRequest(BaseModel):
    campaign_id: uuid.UUID
    batch_size: int = Field(default=10, ge=1, le=100)
    lease_seconds: int = Field(default=30, ge=5, le=300)


class ProgressiveExecuteRequest(BaseModel):
    call_ids: list[uuid.UUID] = Field(min_length=1, max_length=100)


@router.post("/progressive/prepare")
def prepare_progressive_calls(
    data: ProgressivePrepareRequest,
    db: Session = Depends(get_db),
):

    campaign = db.get(Campaign, data.campaign_id)

    if campaign is None:
        raise HTTPException(
            status_code=404,
            detail="Campaign not found"
        )

    if campaign.dialing_mode != DialingMode.PROGRESSIVE:
        raise HTTPException(
            status_code=409,
            detail="Campaign is not configured for Progressive Dialing"
        )

    try:
        calls = ProgressiveDialer.prepare_calls(
            db=db,
            campaign_id=data.campaign_id,
            batch_size=data.batch_size,
            lease_seconds=data.lease_seconds,
        )

        db.commit()

        return {
            "campaign_id": str(data.campaign_id),
            "reserved_count": len(calls),
            "calls": [
                {
                    "call_id": str(call.id),
                    "agent_id": str(call.agent_id),
                    "borrower_id": str(call.borrower_id),
                    "status": call.status.value,
                }
                for call in calls
            ],
        }

    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))

    except Exception:
        db.rollback()
        raise


@router.post("/progressive/execute")
def execute_progressive_calls(
    data: ProgressiveExecuteRequest,
    db: Session = Depends(get_db),
):

    results = []

    for call_id in data.call_ids:

        try:
            result = CallExecutionService.execute_call(
                db=db,
                call_id=call_id,
                provider_manager=provider_manager,
            )

            results.append(result)

        except ValueError as exc:
            db.rollback()

            results.append({
                "success": False,
                "call_id": str(call_id),
                "reason": str(exc),
            })

        except Exception:
            db.rollback()

            results.append({
                "success": False,
                "call_id": str(call_id),
                "reason": "Call execution failed",
            })

    return {
        "requested_count": len(data.call_ids),
        "successful_count": sum(
            1 for result in results
            if result.get("success")
        ),
        "failed_count": sum(
            1 for result in results
            if not result.get("success")
        ),
        "results": results,
    }


@router.get("/providers/health")
def get_provider_health():

    return {
        "providers": provider_manager.get_provider_health()
    }