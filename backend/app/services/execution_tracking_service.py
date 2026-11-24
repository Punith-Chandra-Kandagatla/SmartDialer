
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.call_execution import CallExecution
from app.models.enums import ExecutionStatus


class ExecutionTrackingService:

    @staticmethod
    def get_or_create(
        db: Session,
        call_id: uuid.UUID,
    ) -> CallExecution:

        execution = db.execute(
            select(CallExecution)
            .where(CallExecution.call_id == call_id)
            .with_for_update()
        ).scalar_one_or_none()

        if execution is not None:
            return execution

        execution = CallExecution(
            call_id=call_id,
            status=ExecutionStatus.NOT_STARTED,
            attempt_count=0,
        )

        db.add(execution)
        db.flush()

        return execution

    @staticmethod
    def mark_requesting(
        db: Session,
        execution: CallExecution,
        provider_name: str,
    ) -> None:

        if execution.status != ExecutionStatus.NOT_STARTED:
            raise ValueError(
                f"Cannot start execution from {execution.status.value}"
            )

        now = datetime.now(timezone.utc)

        execution.status = ExecutionStatus.REQUESTING
        execution.provider_name = provider_name
        execution.attempt_count += 1
        execution.request_started_at = now
        execution.response_received_at = None
        execution.last_error = None
        execution.updated_at = now

        db.flush()

    @staticmethod
    def mark_confirmed(
        db: Session,
        execution: CallExecution,
    ) -> None:

        if execution.status not in {
            ExecutionStatus.REQUESTING,
            ExecutionStatus.UNKNOWN,
        }:
            raise ValueError(
                f"Cannot confirm execution from {execution.status.value}"
            )

        now = datetime.now(timezone.utc)

        execution.status = ExecutionStatus.CONFIRMED
        execution.response_received_at = now
        execution.last_error = None
        execution.updated_at = now

        db.flush()

    @staticmethod
    def mark_unknown(
        db: Session,
        execution: CallExecution,
        reason: str,
    ) -> None:

        if execution.status != ExecutionStatus.REQUESTING:
            raise ValueError(
                f"Cannot mark execution UNKNOWN from {execution.status.value}"
            )

        now = datetime.now(timezone.utc)

        execution.status = ExecutionStatus.UNKNOWN
        execution.last_error = reason
        execution.updated_at = now

        db.flush()

    @staticmethod
    def mark_failed(
        db: Session,
        execution: CallExecution,
        reason: str,
    ) -> None:

        if execution.status not in {
            ExecutionStatus.REQUESTING,
            ExecutionStatus.UNKNOWN,
        }:
            raise ValueError(
                f"Cannot mark execution FAILED from {execution.status.value}"
            )

        now = datetime.now(timezone.utc)

        execution.status = ExecutionStatus.FAILED
        execution.response_received_at = now
        execution.last_error = reason
        execution.updated_at = now

        db.flush()