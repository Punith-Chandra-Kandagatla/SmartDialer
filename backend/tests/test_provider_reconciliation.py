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


def test_provider_reconciliation():

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
        # Create test records representing an interrupted execution.
        with SessionLocal() as db:

            campaign = Campaign(
                name=f"Reconciliation Test {test_id}",
                dialing_mode=DialingMode.PROGRESSIVE,
                status=CampaignStatus.RUNNING,
                max_concurrent_calls=1,
            )

            agent = Agent(
                name="Reconciliation Agent",
                email=f"reconcile_{test_id}@test.local",
                status=AgentStatus.RESERVED,
                reservation_token=token,
                reserved_until=(
                    datetime.now(timezone.utc) + timedelta(minutes=5)
                ),
            )

            borrower = Borrower(
                external_ref=f"RECON-{test_id}",
                name="Reconciliation Borrower",
                phone_number="+919888000006",
                status=BorrowerStatus.IN_PROGRESS,
                reservation_token=token,
                reserved_until=(
                    datetime.now(timezone.utc) + timedelta(minutes=5)
                ),
            )

            db.add_all([campaign, agent, borrower])
            db.flush()

            call = Call(
                idempotency_key=f"RECON-CALL-{test_id}",
                campaign_id=campaign.id,
                agent_id=agent.id,
                borrower_id=borrower.id,
                reservation_token=token,
                status=CallStatus.RESERVED,
            )

            db.add(call)
            db.flush()

            # Simulate provider accepting the call.
            original_result = provider.initiate_call(
                borrower.phone_number,
                call.idempotency_key,
            )

            # Simulate SmartDialer losing the provider response.
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
                "Simulated worker crash after provider acceptance",
            )

            db.commit()

            campaign_id = campaign.id
            agent_id = agent.id
            borrower_id = borrower.id
            call_id = call.id

        # Reconcile the uncertain execution.
        with SessionLocal() as db:

            result = ProviderReconciliationService.reconcile_execution(
                db,
                call_id,
                provider_manager,
            )

            assert result["success"] is True
            assert result["outcome"] == "CONFIRMED"

            print("Reconciliation outcome:", result["outcome"])
            print("Recovered provider call ID:", result["provider_call_id"])

        # Verify database state.
        with SessionLocal() as db:

            saved_call = db.get(Call, call_id)
            saved_execution = db.query(CallExecution).filter(
                CallExecution.call_id == call_id
            ).one()

            saved_agent = db.get(Agent, agent_id)
            saved_borrower = db.get(Borrower, borrower_id)

            assert saved_execution.status == ExecutionStatus.CONFIRMED
            assert saved_call.status == CallStatus.INITIATED
            assert saved_call.provider_call_id == original_result.provider_call_id

            assert saved_agent.status == AgentStatus.DIALING
            assert saved_borrower.attempt_count == 1

            assert provider.total_calls == 1

            print("Execution status:", saved_execution.status.value)
            print("Call status:", saved_call.status.value)
            print("Agent status:", saved_agent.status.value)
            print("Actual provider calls:", provider.total_calls)

        print("\nPROVIDER RECONCILIATION TEST PASSED!")

    finally:
        with SessionLocal() as db:

            if call_id is not None:
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
    test_provider_reconciliation()