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


def test_event_processor():

    test_id = uuid.uuid4().hex[:12]

    campaign_id = None
    agent_ids = []
    borrower_ids = []
    original_agents = []
    original_borrowers = []
    call_id = None

    try:
        # Create isolated test resources
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
                name=f"Event Test {test_id}",
                dialing_mode=DialingMode.PROGRESSIVE,
                status=CampaignStatus.RUNNING,
                max_concurrent_calls=1,
            )

            agent = Agent(
                name="Event Test Agent",
                email=f"event_{test_id}@test.local",
                status=AgentStatus.AVAILABLE,
            )

            borrower = Borrower(
                external_ref=f"EVENT-{test_id}",
                name="Event Test Borrower",
                phone_number="+919888000002",
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

        # Initiate the call through the mock provider
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

        # Process provider events
        events = [
    (f"event-{test_id}-1", "RINGING"),
    (f"event-{test_id}-2", "ANSWERED"),
    (f"event-{test_id}-3", "CONNECTED"),
    (f"event-{test_id}-4", "COMPLETED"),
]

        for event_id, event_type in events:

            with SessionLocal() as db:

                result = EventProcessor.process_event(
                    db=db,
                    provider_name="ReliableMock",
                    provider_event_id=event_id,
                    provider_call_id=provider_call_id,
                    event_type=event_type,
                    payload={"event_type": event_type},
                )

                assert result["success"] is True
                assert result["duplicate"] is False

                print(
                    f"{event_type}: "
                    f"PASSED"
                )

        # Verify final database state
        with SessionLocal() as db:

            saved_call = db.get(Call, call_id)
            saved_agent = db.get(Agent, agent_ids[0])
            saved_borrower = db.get(Borrower, borrower_ids[0])

            assert saved_call.status == CallStatus.COMPLETED
            assert saved_agent.status == AgentStatus.WRAP_UP
            assert saved_borrower.status == BorrowerStatus.CONTACTED

            print("\nFinal Call Status:", saved_call.status.value)
            print("Final Agent Status:", saved_agent.status.value)
            print("Final Borrower Status:", saved_borrower.status.value)

        # Verify duplicate event handling
        with SessionLocal() as db:

            duplicate_result = EventProcessor.process_event(
                db=db,
                provider_name="ReliableMock",
                provider_event_id="event-4",
                provider_call_id=provider_call_id,
                event_type="COMPLETED",
                payload={"event_type": "COMPLETED"},
            )

            assert duplicate_result["success"] is True
            assert duplicate_result["duplicate"] is True

            print("\nDuplicate Event Protection: PASSED")

        print("\nEVENT PROCESSOR TEST PASSED!")

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
    test_event_processor()