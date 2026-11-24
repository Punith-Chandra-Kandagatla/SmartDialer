import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.call import Call
from app.models.campaign import Campaign
from app.models.enums import (
    CampaignStatus,
    CallStatus,
    DialingMode,
)

from app.services.reservation_service import ReservationService


class ProgressiveDialer:

    @staticmethod
    def prepare_calls(
        db: Session,
        campaign_id: uuid.UUID,
        batch_size: int = 100,
        lease_seconds: int = 30,
    ) -> list[Call]:

        if batch_size <= 0:
            raise ValueError("batch_size must be positive")

        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")

        # Lock the campaign to serialize concurrent batch requests.
        campaign = db.execute(
            select(Campaign)
            .where(Campaign.id == campaign_id)
            .with_for_update()
        ).scalar_one_or_none()

        if campaign is None:
            return []

        if campaign.status != CampaignStatus.RUNNING:
            return []

        if campaign.dialing_mode != DialingMode.PROGRESSIVE:
            raise ValueError(
                "Progressive Dialer can only run on Progressive campaigns"
            )

        active_statuses = [
            CallStatus.RESERVED,
            CallStatus.INITIATED,
            CallStatus.RINGING,
            CallStatus.ANSWERED,
            CallStatus.CONNECTED,
        ]

        active_calls = db.query(Call).filter(
            Call.campaign_id == campaign_id,
            Call.status.in_(active_statuses),
        ).count()

        remaining_capacity = max(
            0,
            campaign.max_concurrent_calls - active_calls,
        )

        reservation_limit = min(
            batch_size,
            remaining_capacity,
        )

        reserved_calls = []

        for _ in range(reservation_limit):

            call = ReservationService.reserve_next_call(
                db=db,
                campaign_id=campaign_id,
                lease_seconds=lease_seconds,
            )

            if call is None:
                break

            reserved_calls.append(call)

        db.flush()

        return reserved_calls