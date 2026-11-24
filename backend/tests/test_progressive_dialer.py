
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, delete

from app.database.connection import SessionLocal
from app.models.agent import Agent
from app.models.borrower import Borrower
from app.models.campaign import Campaign
from app.models.call import Call
from app.models.enums import (
    AgentStatus,
    BorrowerStatus,
    CampaignStatus,
    DialingMode,
    CallStatus,
)
from app.services.progressive_dialer import ProgressiveDialer
from app.services.reservation_service import ReservationService


def test_progressive_dialer():

    unique_id = uuid.uuid4().hex[:12]

    campaign_id = None
    agent_ids = []
    borrower_ids = []
    original_agent_ids = []
    original_borrower_ids = []

    try:
        # Isolate test resources
        with SessionLocal() as db:

            available_agents = db.scalars(
                select(Agent).where(
                    Agent.status == AgentStatus.AVAILABLE
                )
            ).all()

            eligible_borrowers = db.scalars(
                select(Borrower).where(
                    Borrower.status == BorrowerStatus.ELIGIBLE
                )
            ).all()

            original_agent_ids = [a.id for a in available_agents]
            original_borrower_ids = [b.id for b in eligible_borrowers]

            for agent in available_agents:
                agent.status = AgentStatus.OFFLINE

            for borrower in eligible_borrowers:
                borrower.status = BorrowerStatus.INELIGIBLE

            campaign = Campaign(
                name=f"Progressive Test {unique_id}",
                dialing_mode=DialingMode.PROGRESSIVE,
                status=CampaignStatus.RUNNING,
                max_concurrent_calls=2,
            )

            agents = [
                Agent(
                    name=f"Progressive Agent {i}",
                    email=f"progressive_{unique_id}_{i}@test.local",
                    status=AgentStatus.AVAILABLE,
                )
                for i in range(3)
            ]

            borrowers = [
                Borrower(
                    external_ref=f"PROG-{unique_id}-{i}",
                    name=f"Progressive Borrower {i}",
                    phone_number=f"+91988800000{i}",
                    status=BorrowerStatus.ELIGIBLE,
                )
                for i in range(5)
            ]

            db.add_all([campaign, *agents, *borrowers])
            db.commit()

            campaign_id = campaign.id
            agent_ids = [a.id for a in agents]
            borrower_ids = [b.id for b in borrowers]

        # Prepare progressive calls
        with SessionLocal() as db:

            calls = ProgressiveDialer.prepare_calls(
                db=db,
                campaign_id=campaign_id,
                batch_size=5,
                lease_seconds=60,
            )

            assert len(calls) == 2

            call_ids = [call.id for call in calls]

            db.commit()

        # Verify allocation
        with SessionLocal() as db:

            saved_calls = [
                db.get(Call, call_id)
                for call_id in call_ids
            ]

            assert all(
                call.status == CallStatus.RESERVED
                for call in saved_calls
            )

            allocated_agents = [
                call.agent_id for call in saved_calls
            ]

            allocated_borrowers = [
                call.borrower_id for call in saved_calls
            ]

            assert len(set(allocated_agents)) == 2
            assert len(set(allocated_borrowers)) == 2

            assert set(allocated_agents).issubset(set(agent_ids))
            assert set(allocated_borrowers).issubset(set(borrower_ids))

            print("Reserved calls:", len(saved_calls))
            print("Unique agents allocated:", len(set(allocated_agents)))
            print("Unique borrowers allocated:", len(set(allocated_borrowers)))

        print("\nPROGRESSIVE DIALER TEST PASSED!")

    finally:
        # Clean up dependent records first
        with SessionLocal() as db:

            if campaign_id is not None:

                test_calls = db.scalars(
                    select(Call).where(
                        Call.campaign_id == campaign_id
                    )
                ).all()

                for call in test_calls:
                    if call.status == CallStatus.RESERVED:
                        ReservationService.release_reservation(
                            db,
                            call.id,
                            call.reservation_token,
                            "Progressive test cleanup",
                        )

                db.flush()

                db.execute(
                    delete(Call).where(
                        Call.campaign_id == campaign_id
                    )
                )

                db.execute(
                    delete(Agent).where(
                        Agent.id.in_(agent_ids)
                    )
                )

                db.execute(
                    delete(Borrower).where(
                        Borrower.id.in_(borrower_ids)
                    )
                )

                db.execute(
                    delete(Campaign).where(
                        Campaign.id == campaign_id
                    )
                )

            # Restore original statuses
            for agent in db.scalars(
                select(Agent).where(
                    Agent.id.in_(original_agent_ids)
                )
            ).all():
                agent.status = AgentStatus.AVAILABLE

            for borrower in db.scalars(
                select(Borrower).where(
                    Borrower.id.in_(original_borrower_ids)
                )
            ).all():
                borrower.status = BorrowerStatus.ELIGIBLE

            db.commit()

        print("Test data cleaned up and original statuses restored.")


if __name__ == "__main__":
    test_progressive_dialer()
