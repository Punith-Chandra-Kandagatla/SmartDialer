import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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
from app.services.reservation_service import ReservationService


def test_reservation_flow():

    test_id = uuid.uuid4().hex[:12]

    campaign_id = None
    agent_id = None
    borrower_id = None
    call_id = None

    original_agents = {}
    original_borrowers = {}

    try:
        with SessionLocal() as db:

            # 1. Isolate existing available agents
            available_agents = db.query(Agent).filter(
                Agent.status == AgentStatus.AVAILABLE
            ).all()

            for existing_agent in available_agents:
                original_agents[existing_agent.id] = existing_agent.status
                existing_agent.status = AgentStatus.OFFLINE

            # 2. Isolate existing eligible borrowers
            eligible_borrowers = db.query(Borrower).filter(
                Borrower.status == BorrowerStatus.ELIGIBLE
            ).all()

            for existing_borrower in eligible_borrowers:
                original_borrowers[existing_borrower.id] = (
                    existing_borrower.status
                )
                existing_borrower.status = BorrowerStatus.INELIGIBLE

            # 3. Create unique campaign
            campaign = Campaign(
                name=f"Reservation Test Campaign {test_id}",
                dialing_mode=DialingMode.PROGRESSIVE,
                status=CampaignStatus.RUNNING,
            )

            # 4. Create unique agent
            agent = Agent(
                name=f"Test Agent {test_id}",
                email=f"test.agent.{test_id}@smartdialer.local",
                status=AgentStatus.AVAILABLE,
            )

            # 5. Create unique borrower
            borrower = Borrower(
                external_ref=f"TEST-BORROWER-{test_id}",
                name=f"Test Borrower {test_id}",
                phone_number=f"+919{uuid.uuid4().int % 1000000000:09d}",
                status=BorrowerStatus.ELIGIBLE,
            )

            db.add_all([campaign, agent, borrower])
            db.flush()

            campaign_id = campaign.id
            agent_id = agent.id
            borrower_id = borrower.id

            # Commit isolated test resources
            db.commit()

            # 6. Reserve agent and borrower
            call = ReservationService.reserve_next_call(
                db=db,
                campaign_id=campaign_id,
                lease_seconds=30,
            )

            assert call is not None, "Call reservation failed"

            call_id = call.id

            # Verify reservation ownership
            assert call.agent_id == agent_id
            assert call.borrower_id == borrower_id

            db.commit()

            # 7. Verify persisted data
            saved_call = db.get(Call, call_id)
            saved_agent = db.get(Agent, agent_id)
            saved_borrower = db.get(Borrower, borrower_id)

            assert saved_call.status == CallStatus.RESERVED

            assert saved_agent.status == AgentStatus.RESERVED
            assert saved_borrower.status == BorrowerStatus.IN_PROGRESS

            assert saved_agent.reservation_token is not None
            assert saved_borrower.reservation_token is not None

            assert (
                saved_agent.reservation_token
                == saved_borrower.reservation_token
                == saved_call.reservation_token
            )

            assert saved_agent.reserved_until is not None
            assert saved_borrower.reserved_until is not None

            print("\nRESERVATION TEST PASSED!")
            print("Campaign:", campaign.name)
            print("Agent:", saved_agent.name)
            print("Borrower:", saved_borrower.name)
            print("Call ID:", call_id)
            print("Call status:", saved_call.status.value)
            print("Reservation token consistency: PASSED")

    finally:

        # 8. Clean up test records and restore original resources
        with SessionLocal() as db:

            if call_id is not None:
                db.query(Call).filter(
                    Call.id == call_id
                ).delete(synchronize_session=False)

            # Restore previously available agents
            for existing_id, original_status in original_agents.items():
                existing_agent = db.get(Agent, existing_id)

                if existing_agent is not None:
                    existing_agent.status = original_status

            # Restore previously eligible borrowers
            for existing_id, original_status in original_borrowers.items():
                existing_borrower = db.get(Borrower, existing_id)

                if existing_borrower is not None:
                    existing_borrower.status = original_status

            # Remove test-created resources
            if borrower_id is not None:
                db.query(Borrower).filter(
                    Borrower.id == borrower_id
                ).delete(synchronize_session=False)

            if agent_id is not None:
                db.query(Agent).filter(
                    Agent.id == agent_id
                ).delete(synchronize_session=False)

            if campaign_id is not None:
                db.query(Campaign).filter(
                    Campaign.id == campaign_id
                ).delete(synchronize_session=False)

            db.commit()


if __name__ == "__main__":
    test_reservation_flow()