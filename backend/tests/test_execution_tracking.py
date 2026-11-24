import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete

from app.database.connection import SessionLocal
from app.models.campaign import Campaign
from app.models.borrower import Borrower
from app.models.call import Call
from app.models.call_execution import CallExecution

from app.models.enums import (
    CampaignStatus,
    DialingMode,
    BorrowerStatus,
    ExecutionStatus,
)

from app.services.execution_tracking_service import (
    ExecutionTrackingService,
)


def test_execution_tracking():

    test_id = uuid.uuid4().hex[:12]
    campaign_id = None
    borrower_id = None
    call_id = None

    try:
        # Create test records
        with SessionLocal() as db:

            campaign = Campaign(
                name=f"Execution Tracking {test_id}",
                dialing_mode=DialingMode.PROGRESSIVE,
                status=CampaignStatus.RUNNING,
                max_concurrent_calls=1,
            )

            borrower = Borrower(
                external_ref=f"TRACK-{test_id}",
                name="Tracking Test Borrower",
                phone_number="+919888000004",
                status=BorrowerStatus.ELIGIBLE,
            )

            db.add_all([campaign, borrower])
            db.flush()

            call = Call(
                idempotency_key=f"TRACK-CALL-{test_id}",
                campaign_id=campaign.id,
                borrower_id=borrower.id,
            )

            db.add(call)
            db.commit()

            campaign_id = campaign.id
            borrower_id = borrower.id
            call_id = call.id

        # Test execution lifecycle
        with SessionLocal() as db:

            execution = ExecutionTrackingService.get_or_create(
                db,
                call_id,
            )

            assert execution.status == ExecutionStatus.NOT_STARTED

            ExecutionTrackingService.mark_requesting(
                db,
                execution,
                "ReliableMock",
            )

            assert execution.status == ExecutionStatus.REQUESTING
            assert execution.attempt_count == 1

            ExecutionTrackingService.mark_unknown(
                db,
                execution,
                "Simulated worker crash after provider request",
            )

            assert execution.status == ExecutionStatus.UNKNOWN

            ExecutionTrackingService.mark_confirmed(
                db,
                execution,
            )

            assert execution.status == ExecutionStatus.CONFIRMED

            db.commit()

            print("NOT_STARTED → REQUESTING: PASSED")
            print("REQUESTING → UNKNOWN: PASSED")
            print("UNKNOWN → CONFIRMED: PASSED")

        # Verify persistent database state
        with SessionLocal() as db:

            execution = db.query(CallExecution).filter(
                CallExecution.call_id == call_id
            ).one()

            assert execution.status == ExecutionStatus.CONFIRMED
            assert execution.attempt_count == 1
            assert execution.provider_name == "ReliableMock"
            assert execution.response_received_at is not None

            print("\nPersistent execution status:", execution.status.value)
            print("Attempt count:", execution.attempt_count)

        # Verify duplicate execution creation is prevented
        with SessionLocal() as db:

            existing = ExecutionTrackingService.get_or_create(
                db,
                call_id,
            )

            assert existing.status == ExecutionStatus.CONFIRMED

            db.commit()

            print("Existing execution reused: PASSED")

        print("\nEXECUTION TRACKING TEST PASSED!")

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
    test_execution_tracking()