import sys
from pathlib import Path
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, delete

from app.database.connection import SessionLocal
from app.models.agent import Agent
from app.models.borrower import Borrower
from app.models.campaign import Campaign
from app.models.call import Call
from app.models.call_execution import CallExecution
from app.models.enums import (
    AgentStatus,
    BorrowerStatus,
    CampaignStatus,
    DialingMode,
    CallStatus,
)
from app.services.reservation_service import ReservationService
from app.services.progressive_dialer import ProgressiveDialer
from app.services.call_execution_service import CallExecutionService
from app.providers.provider_manager import ProviderManager
from app.providers.reliable_provider import ReliableMockProvider


def test_call_execution():

    test_id = uuid.uuid4().hex[:12]
    campaign_id = None
    agent_ids = []
    borrower_ids = []
    original_agents = []
    original_borrowers = []

    try:
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

            original_agents = [a.id for a in available_agents]
            original_borrowers = [b.id for b in eligible_borrowers]

            for agent in available_agents:
                agent.status = AgentStatus.OFFLINE

            for borrower in eligible_borrowers:
                borrower.status = BorrowerStatus.INELIGIBLE

            campaign = Campaign(
                name=f"Execution Test {test_id}",
                dialing_mode=DialingMode.PROGRESSIVE,
                status=CampaignStatus.RUNNING,
                max_concurrent_calls=1,
            )

            agent = Agent(
                name="Execution Test Agent",
                email=f"execution_{test_id}@test.local",
                status=AgentStatus.AVAILABLE,
            )

            borrower = Borrower(
                external_ref=f"EXEC-{test_id}",
                name="Execution Test Borrower",
                phone_number="+919888000001",
                status=BorrowerStatus.ELIGIBLE,
            )

            db.add_all([campaign, agent, borrower])
            db.commit()

            campaign_id = campaign.id
            agent_ids = [agent.id]
            borrower_ids = [borrower.id]

        with SessionLocal() as db:

            calls = ProgressiveDialer.prepare_calls(
                db,
                campaign_id,
                batch_size=1,
                lease_seconds=60,
            )

            assert len(calls) == 1
            call_id = calls[0].id
            db.commit()

        provider_manager = ProviderManager()
        provider_manager.register_provider(ReliableMockProvider())

        with SessionLocal() as db:

            result = CallExecutionService.execute_call(
                db,
                call_id,
                provider_manager,
            )

            assert result["success"] is True
            assert result["provider"] == "ReliableMock"

            saved_call = db.get(Call, call_id)
            saved_agent = db.get(Agent, agent_ids[0])

            assert saved_call.status == CallStatus.INITIATED
            assert saved_agent.status == AgentStatus.DIALING

            print("Provider:", result["provider"])
            print("Call status:", saved_call.status.value)
            print("Agent status:", saved_agent.status.value)

        print("\nCALL EXECUTION TEST PASSED!")

    finally:
        with SessionLocal() as db:

            if campaign_id is not None:

                calls = db.scalars(
                    select(Call).where(
                        Call.campaign_id == campaign_id
                    )
                ).all()

                for call in calls:
                    if call.status == CallStatus.RESERVED:
                        ReservationService.release_reservation(
                            db,
                            call.id,
                            call.reservation_token,
                            "Test cleanup",
                        )

                db.flush()

                db.execute(
                    delete(CallExecution).where(
                        CallExecution.call_id.in_(
                            select(Call.id).where(
                                Call.campaign_id == campaign_id
                            )
                        )
                    )
                )

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

            for agent in db.scalars(
                select(Agent).where(
                    Agent.id.in_(original_agents)
                )
            ).all():
                agent.status = AgentStatus.AVAILABLE

            for borrower in db.scalars(
                select(Borrower).where(
                    Borrower.id.in_(original_borrowers)
                )
            ).all():
                borrower.status = BorrowerStatus.ELIGIBLE

            db.commit()

        print("Test data cleaned up.")


if __name__ == "__main__":
    test_call_execution()