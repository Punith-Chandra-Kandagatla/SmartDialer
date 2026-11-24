import sys
import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete

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
    ExecutionStatus,
)

from app.services.execution_tracking_service import (
    ExecutionTrackingService,
)

from app.services.provider_reconciliation_service import (
    ProviderReconciliationService,
)

from app.providers.provider_manager import ProviderManager
from app.providers.reliable_provider import ReliableMockProvider


def test_unresolved_reconciliation():

    test_id = uuid.uuid4().hex[:12]
    token = uuid.uuid4()

    campaign_id = None
    agent_id = None
    borrower_id = None
    call_id = None

    provider = ReliableMockProvider()

    provider_manager = ProviderManager()
    provider_manager.register_provider(provider)

    try:
        # Create an interrupted execution with no provider call.
        with SessionLocal() as db:

            campaign = Campaign(
                name=f"Unresolved Test {test_id}",
                dialing_mode=DialingMode.PROGRESSIVE,
                status=CampaignStatus.RUNNING,
                max_concurrent_calls=1,
            )

            agent = Agent(
                name="Unresolved Agent",
                email=f"unresolved_{test_id}@test.local",
                status=AgentStatus.RESERVED,
                reservation_token=token,
                reserved_until=(
                    datetime.now(timezone.utc) + timedelta(minutes=5)
                ),
            )

            borrower = Borrower(
                external_ref=f"UNRES-{test_id}",
                name="Unresolved Borrower",
                phone_number="+919888000007",
                status=BorrowerStatus.IN_PROGRESS,
                reservation_token=token,
                reserved_until=(
                    datetime.now(timezone.utc) + timedelta(minutes=5)
                ),
            )

            db.add_all([campaign, agent, borrower])
            db.flush()

            call = Call(
                idempotency_key=f"UNRES-CALL-{test_id}",
                campaign_id=campaign.id,
                agent_id=agent.id,
                borrower_id=borrower.id,
                reservation_token=token,
                status=CallStatus.RESERVED,
            )

            db.add(call)
            db.flush()

            execution = ExecutionTrackingService.get_or_create(
                db,
                call.id,
            )

            ExecutionTrackingService.mark_requesting(
                db,
                execution,
                provider.provider_name,
            )

            ExecutionTrackingService.mark_unknown(
                db,
                execution,
                "Simulated worker crash",
            )

            db.commit()

            campaign_id = campaign.id
            agent_id = agent.id
            borrower_id = borrower.id
            call_id = call.id

        # Provider has no record of this call.
        with SessionLocal() as db:

            result = ProviderReconciliationService.reconcile_execution(
                db,
                call_id,
                provider_manager,
            )

            assert result["success"] is False
            assert result["outcome"] == "UNKNOWN"

            print("Reconciliation outcome:", result["outcome"])
            print("Reason:", result["reason"])

        # Verify that no resources were released.
        with SessionLocal() as db:

            saved_call = db.get(Call, call_id)
            saved_execution = db.query(CallExecution).filter(
                CallExecution.call_id == call_id
            ).one()

            saved_agent = db.get(Agent, agent_id)
            saved_borrower = db.get(Borrower, borrower_id)

            assert saved_execution.status == ExecutionStatus.UNKNOWN
            assert saved_call.status == CallStatus.RESERVED

            assert saved_agent.status == AgentStatus.RESERVED
            assert saved_borrower.status == BorrowerStatus.IN_PROGRESS

            assert saved_agent.reservation_token == token
            assert saved_borrower.reservation_token == token

            assert provider.total_calls == 0

            print("Execution status:", saved_execution.status.value)
            print("Call status:", saved_call.status.value)
            print("Agent status:", saved_agent.status.value)
            print("Borrower status:", saved_borrower.status.value)
            print("New outbound calls:", provider.total_calls)

        print("\nUNRESOLVED RECONCILIATION TEST PASSED!")

    finally:
        with SessionLocal() as db:

            if call_id is not None:
                db.execute(
                    delete(CallExecution).where(
                        CallExecution.call_id == call_id
                    )
                )

                db.execute(
                    delete(Call).where(Call.id == call_id)
                )

            if agent_id is not None:
                db.execute(
                    delete(Agent).where(Agent.id == agent_id)
                )

            if borrower_id is not None:
                db.execute(
                    delete(Borrower).where(
                        Borrower.id == borrower_id
                    )
                )

            if campaign_id is not None:
                db.execute(
                    delete(Campaign).where(
                        Campaign.id == campaign_id
                    )
                )

            db.commit()

        print("Test data cleaned up.")


if __name__ == "__main__":
    test_unresolved_reconciliation()