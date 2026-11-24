from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.call_execution import CallExecution
from app.models.enums import ExecutionStatus

from app.services.execution_tracking_service import (
    ExecutionTrackingService,
)


class ExecutionRecoveryService:

    @staticmethod
    def recover_stale_executions(
        db: Session,
        timeout_seconds: int = 60,
        batch_size: int = 100,
    ) -> int:

        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        if batch_size <= 0:
            raise ValueError("batch_size must be positive")

        cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=timeout_seconds
        )

        executions = db.execute(
            select(CallExecution)
            .where(
                CallExecution.status == ExecutionStatus.REQUESTING,
                CallExecution.request_started_at <= cutoff,
            )
            .order_by(CallExecution.request_started_at)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        ).scalars().all()

        recovered_count = 0

        for execution in executions:

            ExecutionTrackingService.mark_unknown(
                db,
                execution,
                "Worker execution timed out. Provider outcome requires reconciliation.",
            )

            recovered_count += 1

        db.flush()

        return recovered_count