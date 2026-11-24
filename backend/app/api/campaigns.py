from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.enums import CampaignStatus
from app.schemas.campaign import (
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
)
from app.services.campaign_service import CampaignService


router = APIRouter(
    prefix="/api/v1/campaigns",
    tags=["Campaign Management"],
)


@router.post("/", response_model=CampaignResponse, status_code=201)
def create_campaign(
    data: CampaignCreate,
    db: Session = Depends(get_db),
):
    return CampaignService.create_campaign(db, data)


@router.get("/", response_model=list[CampaignResponse])
def list_campaigns(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return CampaignService.list_campaigns(db, limit, offset)


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),
):
    campaign = CampaignService.get_campaign(db, campaign_id)

    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return campaign


@router.patch("/{campaign_id}", response_model=CampaignResponse)
def update_campaign(
    campaign_id: UUID,
    data: CampaignUpdate,
    db: Session = Depends(get_db),
):
    try:
        campaign = CampaignService.update_campaign(
            db, campaign_id, data
        )

        if campaign is None:
            raise HTTPException(
                status_code=404,
                detail="Campaign not found",
            )

        return campaign

    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.patch("/{campaign_id}/status", response_model=CampaignResponse)
def change_campaign_status(
    campaign_id: UUID,
    status: CampaignStatus,
    db: Session = Depends(get_db),
):
    try:
        campaign = CampaignService.change_campaign_status(
            db, campaign_id, status
        )

        if campaign is None:
            raise HTTPException(
                status_code=404,
                detail="Campaign not found",
            )

        return campaign

    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))