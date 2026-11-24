import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.borrower import Borrower
from app.models.call import Call
from app.models.campaign import Campaign
from app.models.enums import (
    AgentStatus,
    BorrowerStatus,
    CallStatus,
    CampaignStatus,
)


class ReservationService:

    @staticmethod
    def reserve_next_call(
        db: Session,
        campaign_id: uuid.UUID,
        lease_seconds: int = 30,
    ) -> Call | None:

        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")

        now = datetime.now(timezone.utc)
        reservation_expiry = now + timedelta(seconds=lease_seconds)

        campaign = db.execute(
            select(Campaign).where(
                Campaign.id == campaign_id,
                Campaign.status == CampaignStatus.RUNNING,
            )
        ).scalar_one_or_none()

        if campaign is None:
            return None

        agent = db.execute(
            select(Agent)
            .where(
                Agent.status == AgentStatus.AVAILABLE,
                Agent.reservation_token.is_(None),
            )
            .order_by(Agent.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        ).scalar_one_or_none()

        if agent is None:
            return None

        borrower = db.execute(
            select(Borrower)
            .where(
                Borrower.status == BorrowerStatus.ELIGIBLE,
                Borrower.is_active.is_(True),
                Borrower.attempt_count < Borrower.max_attempts,
                Borrower.reservation_token.is_(None),
                (
                    Borrower.next_eligible_at.is_(None)
                    | (Borrower.next_eligible_at <= now)
                ),
            )
            .order_by(Borrower.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        ).scalar_one_or_none()

        if borrower is None:
            return None

        reservation_token = uuid.uuid4()

        agent.status = AgentStatus.RESERVED
        agent.reservation_token = reservation_token
        agent.reserved_until = reservation_expiry

        borrower.status = BorrowerStatus.IN_PROGRESS
        borrower.reservation_token = reservation_token
        borrower.reserved_until = reservation_expiry

        call = Call(
            idempotency_key=str(uuid.uuid4()),
            campaign_id=campaign.id,
            agent_id=agent.id,
            borrower_id=borrower.id,
            reservation_token=reservation_token,
            status=CallStatus.RESERVED,
            attempt_number=borrower.attempt_count + 1,
            reserved_at=now,
        )

        db.add(call)
        db.flush()

        return call

    @staticmethod
    def release_reservation(
        db: Session,
        call_id: uuid.UUID,
        reservation_token: uuid.UUID,
        failure_reason: str,
    ) -> bool:

        call = db.execute(
            select(Call)
            .where(Call.id == call_id)
            .with_for_update()
        ).scalar_one_or_none()

        if call is None or call.status != CallStatus.RESERVED:
            return False

        if call.reservation_token != reservation_token:
            return False

        agent = db.execute(
            select(Agent)
            .where(Agent.id == call.agent_id)
            .with_for_update()
        ).scalar_one_or_none()

        borrower = db.execute(
            select(Borrower)
            .where(Borrower.id == call.borrower_id)
            .with_for_update()
        ).scalar_one_or_none()

        if (
            agent is None
            or borrower is None
            or agent.reservation_token != reservation_token
            or borrower.reservation_token != reservation_token
        ):
            return False

        now = datetime.now(timezone.utc)

        agent.status = AgentStatus.AVAILABLE
        agent.reservation_token = None
        agent.reserved_until = None

        borrower.status = BorrowerStatus.ELIGIBLE
        borrower.reservation_token = None
        borrower.reserved_until = None

        call.status = CallStatus.CANCELLED
        call.failure_reason = failure_reason
        call.completed_at = now

        db.flush()

        return True

    @staticmethod
    def recover_expired_reservations(
        db: Session,
        batch_size: int = 100,
    ) -> int:
        """
        Recover expired RESERVED calls.

        Uses SKIP LOCKED so multiple recovery workers
        can process different calls concurrently.

        The caller must commit or roll back the transaction.
        """

        if batch_size <= 0:
            raise ValueError("batch_size must be positive")

        now = datetime.now(timezone.utc)

        expired_calls = db.execute(
            select(Call)
            .join(Agent, Call.agent_id == Agent.id)
            .join(Borrower, Call.borrower_id == Borrower.id)
            .where(
                Call.status == CallStatus.RESERVED,
                Call.reservation_token.is_not(None),
                Agent.reservation_token == Call.reservation_token,
                Borrower.reservation_token == Call.reservation_token,
                Agent.reserved_until <= now,
                Borrower.reserved_until <= now,
            )
            .order_by(Agent.reserved_until)
            .limit(batch_size)
            .with_for_update(of=Call, skip_locked=True)
        ).scalars().all()

        recovered_count = 0

        for call in expired_calls:

            token = call.reservation_token

            agent = db.execute(
                select(Agent)
                .where(Agent.id == call.agent_id)
                .with_for_update()
            ).scalar_one_or_none()

            borrower = db.execute(
                select(Borrower)
                .where(Borrower.id == call.borrower_id)
                .with_for_update()
            ).scalar_one_or_none()

            # Revalidate ownership and expiry after obtaining locks.
            if (
                agent is None
                or borrower is None
                or agent.reservation_token != token
                or borrower.reservation_token != token
                or agent.reserved_until is None
                or borrower.reserved_until is None
                or agent.reserved_until > now
                or borrower.reserved_until > now
                or call.status != CallStatus.RESERVED
            ):
                continue

            # Release agent
            agent.status = AgentStatus.AVAILABLE
            agent.reservation_token = None
            agent.reserved_until = None

            # Release borrower
            borrower.status = BorrowerStatus.ELIGIBLE
            borrower.reservation_token = None
            borrower.reserved_until = None

            # Mark abandoned call
            call.status = CallStatus.CANCELLED
            call.failure_reason = "Reservation lease expired"
            call.completed_at = now

            recovered_count += 1

        db.flush()

        return recovered_count