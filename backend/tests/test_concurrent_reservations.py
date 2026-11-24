import sys
import uuid
from pathlib import Path
from threading import Barrier
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, func, or_, delete

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


def test_concurrent_reservations():

    unique_id = uuid.uuid4().hex[:12]

    campaign_id = None
    agent_id = None
    borrower_id = None
    original_agent_ids = []
    original_borrower_ids = []

    try:
        # Isolate the test resources
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
                name=f"Concurrency Test {unique_id}",
                dialing_mode=DialingMode.PROGRESSIVE,
                status=CampaignStatus.RUNNING,
            )

            agent = Agent(
                name="Concurrency Test Agent",
                email=f"concurrency_{unique_id}@smartdialer.local",
                status=AgentStatus.AVAILABLE,
            )

            borrower = Borrower(
                external_ref=f"CONCURRENCY-{unique_id}",
                name="Concurrency Test Borrower",
                phone_number="+919777777777",
                status=BorrowerStatus.ELIGIBLE,
            )

            db.add_all([campaign, agent, borrower])
            db.commit()

            campaign_id = campaign.id
            agent_id = agent.id
            borrower_id = borrower.id

        # Synchronize both workers
        barrier = Barrier(2)

        def worker(worker_id):

            with SessionLocal() as db:

                try:
                    barrier.wait(timeout=10)

                    call = ReservationService.reserve_next_call(
                        db=db,
                        campaign_id=campaign_id,
                        lease_seconds=60,
                    )

                    if call is None:
                        db.commit()
                        return {
                            "worker": worker_id,
                            "result": "NO_RESERVATION",
                        }

                    call_id = str(call.id)

                    db.commit()

                    return {
                        "worker": worker_id,
                        "result": "RESERVED",
                        "call_id": call_id,
                    }

                except Exception:
                    db.rollback()
                    raise

        # Run two independent database workers
        with ThreadPoolExecutor(max_workers=2) as executor:

            futures = [
                executor.submit(worker, 1),
                executor.submit(worker, 2),
            ]

            results = [future.result() for future in futures]

        print("\nWorker Results:")

        for result in results:
            print(result)

        successful = [
            r for r in results
            if r["result"] == "RESERVED"
        ]

        unsuccessful = [
            r for r in results
            if r["result"] == "NO_RESERVATION"
        ]

        assert len(successful) == 1, (
            f"Expected 1 successful worker, got {len(successful)}"
        )

        assert len(unsuccessful) == 1, (
            f"Expected 1 unsuccessful worker, got {len(unsuccessful)}"
        )

        # Verify database consistency
        with SessionLocal() as db:

            active_count = db.execute(
                select(func.count())
                .select_from(Call)
                .where(
                    Call.agent_id == agent_id,
                    Call.borrower_id == borrower_id,
                    Call.status.in_([
                        CallStatus.RESERVED,
                        CallStatus.INITIATED,
                        CallStatus.RINGING,
                        CallStatus.ANSWERED,
                        CallStatus.CONNECTED,
                    ]),
                )
            ).scalar_one()

            saved_agent = db.get(Agent, agent_id)
            saved_borrower = db.get(Borrower, borrower_id)

            assert active_count == 1
            assert saved_agent.status == AgentStatus.RESERVED
            assert saved_borrower.status == BorrowerStatus.IN_PROGRESS

            assert (
                saved_agent.reservation_token
                == saved_borrower.reservation_token
            )

            print("\nActive calls:", active_count)
            print("Agent status:", saved_agent.status.value)
            print("Borrower status:", saved_borrower.status.value)

        print("\nCONCURRENT RESERVATION TEST PASSED!")

    finally:
        # Always clean up test records and restore original statuses
        with SessionLocal() as db:

            if agent_id is not None and borrower_id is not None:

                # Delete dependent call records first
                db.execute(
                    delete(Call).where(
                        or_(
                            Call.agent_id == agent_id,
                            Call.borrower_id == borrower_id,
                        )
                    )
                )

                db.flush()

                # Delete test agent, borrower and campaign
                db.execute(
                    delete(Agent).where(Agent.id == agent_id)
                )

                db.execute(
                    delete(Borrower).where(Borrower.id == borrower_id)
                )

                db.execute(
                    delete(Campaign).where(Campaign.id == campaign_id)
                )

            # Restore original agent statuses
            for agent in db.scalars(
                select(Agent).where(
                    Agent.id.in_(original_agent_ids)
                )
            ).all():
                agent.status = AgentStatus.AVAILABLE

            # Restore original borrower statuses
            for borrower in db.scalars(
                select(Borrower).where(
                    Borrower.id.in_(original_borrower_ids)
                )
            ).all():
                borrower.status = BorrowerStatus.ELIGIBLE

            db.commit()

        print("\nTest data cleaned up and original statuses restored.")


if __name__ == "__main__":
    test_concurrent_reservations()
