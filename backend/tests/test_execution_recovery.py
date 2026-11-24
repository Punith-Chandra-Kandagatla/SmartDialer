import sys
import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, delete

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

from app.services.execution_recovery_service import (
    ExecutionRecoveryService,
)


def test_execution_recovery():

    test_id = uuid.uuid4().hex[:12]

    campaign_id = None
    borrower_id = None
    call_id = None

    try:
        # Create test records
        with SessionLocal() as db:

            campaign = Campaign(
                name=f"Recovery Test {test_id}",
                dialing_mode=DialingMode.PROGRESSIVE,
                status=CampaignStatus.RUNNING,
                max_concurrent_calls=1,
            )

            borrower = Borrower(
                external_ref=f"REC-{test_id}",
                name="Recovery Test Borrower",
                phone_number="+919888000005",
                status=BorrowerStatus.ELIGIBLE,
            )

            db.add_all([campaign, borrower])
            db.flush()

            call = Call(
                idempotency_key=f"REC-CALL-{test_id}",
                campaign_id=campaign.id,
                borrower_id=borrower.id,
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
                "ReliableMock",
            )

            # Simulate a worker that stopped responding
            execution.request_started_at = (
                datetime.now(timezone.utc) - timedelta(minutes=5)
            )

            db.commit()

            campaign_id = campaign.id
            borrower_id = borrower.id
            call_id = call.id

        # Run recovery worker
        with SessionLocal() as db:

            recovered_count = (
                ExecutionRecoveryService.recover_stale_executions(
                    db,
                    timeout_seconds=60,
                    batch_size=100,
                )
            )

            db.commit()

            assert recovered_count >= 1

            print("Recovered executions:", recovered_count)

        # Verify persistent state
        with SessionLocal() as db:

            execution = db.execute(
                select(CallExecution).where(
                    CallExecution.call_id == call_id
                )
            ).scalar_one()

            assert execution.status == ExecutionStatus.UNKNOWN

            assert "reconciliation" in execution.last_error.lower()

            print("Execution status:", execution.status.value)
            print("Recovery reason:", execution.last_error)

        # Verify recovery is idempotent
        with SessionLocal() as db:

            recovered_again = (
                ExecutionRecoveryService.recover_stale_executions(
                    db,
                    timeout_seconds=60,
                    batch_size=100,
                )
            )

            db.commit()

            assert recovered_again == 0

            print("Repeated recovery does not reprocess: PASSED")

        print("\nEXECUTION RECOVERY TEST PASSED!")

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
    test_execution_recovery()