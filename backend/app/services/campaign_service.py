import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.models.enums import CampaignStatus

from app.schemas.campaign import (
    CampaignCreate,
    CampaignUpdate,
)


class CampaignService:

    @staticmethod
    def create_campaign(
        db: Session,
        data: CampaignCreate,
    ) -> Campaign:

        campaign = Campaign(**data.model_dump())

        db.add(campaign)
        db.commit()
        db.refresh(campaign)

        return campaign

    @staticmethod
    def get_campaign(
        db: Session,
        campaign_id: uuid.UUID,
    ) -> Campaign | None:

        return db.execute(
            select(Campaign).where(
                Campaign.id == campaign_id
            )
        ).scalar_one_or_none()

    @staticmethod
    def list_campaigns(
        db: Session,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Campaign]:

        if limit <= 0 or limit > 500:
            raise ValueError("Limit must be between 1 and 500")

        if offset < 0:
            raise ValueError("Offset cannot be negative")

        return db.scalars(
            select(Campaign)
            .order_by(Campaign.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).all()

    @staticmethod
    def update_campaign(
        db: Session,
        campaign_id: uuid.UUID,
        data: CampaignUpdate,
    ) -> Campaign | None:

        campaign = db.execute(
            select(Campaign)
            .where(Campaign.id == campaign_id)
            .with_for_update()
        ).scalar_one_or_none()

        if campaign is None:
            return None

        if campaign.status != CampaignStatus.DRAFT:
            raise ValueError(
                "Only draft campaigns can be modified"
            )

        updates = data.model_dump(exclude_unset=True)

        for field, value in updates.items():
            setattr(campaign, field, value)

        db.commit()
        db.refresh(campaign)

        return campaign

    @staticmethod
    def change_campaign_status(
        db: Session,
        campaign_id: uuid.UUID,
        new_status: CampaignStatus,
    ) -> Campaign | None:

        campaign = db.execute(
            select(Campaign)
            .where(Campaign.id == campaign_id)
            .with_for_update()
        ).scalar_one_or_none()

        if campaign is None:
            return None

        allowed_transitions = {
            CampaignStatus.DRAFT: {
                CampaignStatus.RUNNING,
            },
            CampaignStatus.RUNNING: {
                CampaignStatus.PAUSED,
                CampaignStatus.COMPLETED,
            },
            CampaignStatus.PAUSED: {
                CampaignStatus.RUNNING,
                CampaignStatus.COMPLETED,
            },
            CampaignStatus.COMPLETED: set(),
        }

        if new_status not in allowed_transitions[campaign.status]:
            raise ValueError(
                f"Invalid campaign transition: "
                f"{campaign.status.value} -> {new_status.value}"
            )

        campaign.status = new_status

        db.commit()
        db.refresh(campaign)

        return campaign