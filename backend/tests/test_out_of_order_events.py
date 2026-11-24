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
from app.models.provider_event import ProviderEvent
from app.models.call_execution import CallExecution

from app.models.enums import (
    AgentStatus,
    BorrowerStatus,
    CampaignStatus,
    DialingMode,
    CallStatus,
)

from app.services.progressive_dialer import ProgressiveDialer
from app.services.call_execution_service import CallExecutionService
from app.services.event_processor import EventProcessor

from app.providers.provider_manager import ProviderManager
from app.providers.reliable_provider import ReliableMockProvider


def test_out_of_order_events():

    test_id = uuid.uuid4().hex[:12]

    campaign_id = None
    call_id = None
    agent_ids = []
    borrower_ids = []
    original_agents = []
    original_borrowers = []

    try:
        # Create isolated test data
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
                name=f"Out Of Order Test {test_id}",
                dialing_mode=DialingMode.PROGRESSIVE,
                status=CampaignStatus.RUNNING,
                max_concurrent_calls=1,
            )

            agent = Agent(
                name="Out Of Order Agent",
                email=f"outoforder_{test_id}@test.local",
                status=AgentStatus.AVAILABLE,
            )

            borrower = Borrower(
                external_ref=f"OUT-{test_id}",
                name="Out Of Order Borrower",
                phone_number="+919888000003",
                status=BorrowerStatus.ELIGIBLE,
            )

            db.add_all([campaign, agent, borrower])
            db.commit()

            campaign_id = campaign.id
            agent_ids = [agent.id]
            borrower_ids = [borrower.id]

        # Reserve a call
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

        # Initiate outbound call
        provider_manager = ProviderManager()
        provider_manager.register_provider(ReliableMockProvider())

        with SessionLocal() as db:

            execution = CallExecutionService.execute_call(
                db,
                call_id,
                provider_manager,
            )

            assert execution["success"] is True

            provider_call_id = execution["provider_call_id"]

        # ANSWERED arrives before RINGING
        with SessionLocal() as db:

            result = EventProcessor.process_event(
                db,
                "ReliableMock",
                f"out-of-order-{test_id}",
                provider_call_id,
                "ANSWERED",
                {"event_type": "ANSWERED"},
            )

            assert result["success"] is True

            saved_call = db.get(Call, call_id)

            assert saved_call.status == CallStatus.ANSWERED

            print("Early ANSWERED event: PASSED")

        # Late RINGING event must not move state backwards
        with SessionLocal() as db:

            result = EventProcessor.process_event(
                db,
                "ReliableMock",
                f"out-of-order-late-{test_id}",
                provider_call_id,
                "RINGING",
                {"event_type": "RINGING"},
            )

            assert result["success"] is False

            saved_call = db.get(Call, call_id)

            assert saved_call.status == CallStatus.ANSWERED

            print("Late RINGING event rejected: PASSED")

        # CONNECTED arrives
        with SessionLocal() as db:

            result = EventProcessor.process_event(
                db,
                "ReliableMock",
                f"out-of-order-connected-{test_id}",
                provider_call_id,
                "CONNECTED",
                {"event_type": "CONNECTED"},
            )

            assert result["success"] is True

            saved_call = db.get(Call, call_id)

            assert saved_call.status == CallStatus.CONNECTED

            print("CONNECTED event: PASSED")

        # COMPLETED arrives
        with SessionLocal() as db:

            result = EventProcessor.process_event(
                db,
                "ReliableMock",
                f"out-of-order-completed-{test_id}",
                provider_call_id,
                "COMPLETED",
                {"event_type": "COMPLETED"},
            )

            assert result["success"] is True

            saved_call = db.get(Call, call_id)

            assert saved_call.status == CallStatus.COMPLETED

            print("COMPLETED event: PASSED")

        # Verify final states
        with SessionLocal() as db:

            saved_call = db.get(Call, call_id)
            saved_agent = db.get(Agent, agent_ids[0])
            saved_borrower = db.get(Borrower, borrower_ids[0])

            assert saved_call.status == CallStatus.COMPLETED
            assert saved_agent.status == AgentStatus.WRAP_UP
            assert saved_borrower.status == BorrowerStatus.CONTACTED

            print("\nFinal Call:", saved_call.status.value)
            print("Final Agent:", saved_agent.status.value)
            print("Final Borrower:", saved_borrower.status.value)

        print("\nOUT-OF-ORDER EVENT TEST PASSED!")

    finally:

        with SessionLocal() as db:

            if campaign_id is not None:

                if call_id is not None:

                    db.execute(
                        delete(ProviderEvent).where(
                            ProviderEvent.call_id == call_id
                        )
                    )

                    db.execute(
                        delete(CallExecution).where(
                            CallExecution.call_id == call_id
                        )
                    )
                    
                    db.execute(
                        delete(Call).where(
                            Call.id == call_id
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
    test_out_of_order_events()