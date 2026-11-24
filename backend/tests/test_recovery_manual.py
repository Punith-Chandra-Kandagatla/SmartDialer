import sys
import time
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


def test_expired_reservation_recovery():

    unique_id = uuid.uuid4().hex[:12]

    with SessionLocal() as db:

        # Create independent test records
        campaign = Campaign(
            name=f"Recovery Test {unique_id}",
            dialing_mode=DialingMode.PROGRESSIVE,
            status=CampaignStatus.RUNNING,
        )

        agent = Agent(
            name="Recovery Test Agent",
            email=f"recovery_{unique_id}@smartdialer.local",
            status=AgentStatus.AVAILABLE,
        )

        borrower = Borrower(
            external_ref=f"RECOVERY-{unique_id}",
            name="Recovery Test Borrower",
            phone_number="+919888888888",
            status=BorrowerStatus.ELIGIBLE,
        )

        db.add_all([campaign, agent, borrower])
        db.commit()

        campaign_id = campaign.id
        agent_id = agent.id
        borrower_id = borrower.id

        # Reserve resources with a one-second lease
        call = ReservationService.reserve_next_call(
            db=db,
            campaign_id=campaign_id,
            lease_seconds=1,
        )

        assert call is not None

        call_id = call.id
        db.commit()

    print("Reservation created successfully.")

    # Simulate worker crash by waiting for lease expiry
    time.sleep(2)

    with SessionLocal() as db:

        recovered_count = (
            ReservationService.recover_expired_reservations(
                db=db,
                batch_size=10,
            )
        )

        db.commit()

        assert recovered_count == 1

        print("Expired reservations recovered:", recovered_count)

    # Verify persisted state in a fresh session
    with SessionLocal() as db:

        saved_agent = db.get(Agent, agent_id)
        saved_borrower = db.get(Borrower, borrower_id)
        saved_call = db.get(Call, call_id)

        assert saved_agent.status == AgentStatus.AVAILABLE
        assert saved_agent.reservation_token is None
        assert saved_agent.reserved_until is None

        assert saved_borrower.status == BorrowerStatus.ELIGIBLE
        assert saved_borrower.reservation_token is None
        assert saved_borrower.reserved_until is None

        assert saved_call.status == CallStatus.CANCELLED
        assert saved_call.failure_reason == "Reservation lease expired"

        print("Agent status:", saved_agent.status.value)
        print("Borrower status:", saved_borrower.status.value)
        print("Call status:", saved_call.status.value)

    print("\nReservation recovery test PASSED!")


if __name__ == "__main__":
    test_expired_reservation_recovery()