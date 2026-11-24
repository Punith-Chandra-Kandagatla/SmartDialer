import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.borrower import Borrower
from app.models.call import Call
from app.models.call_execution import CallExecution

from app.models.enums import (
    AgentStatus,
    BorrowerStatus,
    CallStatus,
    ExecutionStatus,
)

from app.services.state_machine import StateMachine

from app.services.execution_tracking_service import (
    ExecutionTrackingService,
)

from app.providers.provider_manager import ProviderManager


class ProviderReconciliationService:

    @staticmethod
    def reconcile_execution(
        db: Session,
        call_id: uuid.UUID,
        provider_manager: ProviderManager,
    ) -> dict:
        """
        Reconcile an UNKNOWN execution with its telecom provider.

        The provider lookup happens outside the database transaction.
        The caller controls the final transaction commit.
        """

        # Phase 1: Read the execution and obtain lookup details.
        execution = db.execute(
            select(CallExecution)
            .where(CallExecution.call_id == call_id)
        ).scalar_one_or_none()

        if execution is None:
            return {
                "success": False,
                "reason": "Execution record not found",
            }

        if execution.status != ExecutionStatus.UNKNOWN:
            return {
                "success": False,
                "reason": "Only UNKNOWN executions can be reconciled",
                "status": execution.status.value,
            }

        call = db.get(Call, call_id)

        if call is None:
            return {
                "success": False,
                "reason": "Associated call not found",
            }

        provider_name = execution.provider_name
        idempotency_key = call.idempotency_key

        # End the read transaction before external provider lookup.
        db.rollback()

        if not provider_name:
            return {
                "success": False,
                "reason": "Execution has no associated provider",
            }

        # Phase 2: Query the provider outside the DB transaction.
        try:
            provider = provider_manager.get_provider(provider_name)

            result = provider.find_call_by_idempotency_key(
                idempotency_key
            )

        except Exception as exc:
            return {
                "success": False,
                "outcome": "UNKNOWN",
                "reason": f"Provider reconciliation failed: {exc}",
            }

        if result is None:
            return {
                "success": False,
                "outcome": "UNKNOWN",
                "reason": "Provider has no matching call record. "
                          "Automatic retry is not permitted.",
            }

        # Phase 3: Lock and revalidate records before updating.
        try:
            with db.begin():

                execution = db.execute(
                    select(CallExecution)
                    .where(CallExecution.call_id == call_id)
                    .with_for_update()
                ).scalar_one()

                call = db.execute(
                    select(Call)
                    .where(Call.id == call_id)
                    .with_for_update()
                ).scalar_one()

                if execution.status != ExecutionStatus.UNKNOWN:
                    raise ValueError(
                        "Execution status changed during reconciliation"
                    )

                agent = db.execute(
                    select(Agent)
                    .where(Agent.id == call.agent_id)
                    .with_for_update()
                ).scalar_one()

                borrower = db.execute(
                    select(Borrower)
                    .where(Borrower.id == call.borrower_id)
                    .with_for_update()
                ).scalar_one()

                if not result.success:
                    ExecutionTrackingService.mark_failed(
                        db,
                        execution,
                        result.error_message or "Provider confirmed failure",
                    )

                    StateMachine.transition_call(
                        call,
                        CallStatus.FAILED,
                        failure_reason=result.error_message,
                    )

                    agent.status = AgentStatus.AVAILABLE
                    agent.reservation_token = None
                    agent.reserved_until = None

                    borrower.attempt_count += 1

                    borrower.status = (
                        BorrowerStatus.ELIGIBLE
                        if borrower.attempt_count < borrower.max_attempts
                        else BorrowerStatus.INELIGIBLE
                    )

                    borrower.reservation_token = None
                    borrower.reserved_until = None

                    return {
                        "success": True,
                        "outcome": "FAILED",
                        "reason": result.error_message,
                    }

                if (
                    call.status != CallStatus.RESERVED
                    or agent.status != AgentStatus.RESERVED
                    or borrower.status != BorrowerStatus.IN_PROGRESS
                    or agent.reservation_token != call.reservation_token
                    or borrower.reservation_token != call.reservation_token
                ):
                    raise ValueError(
                        "Call or resource reservation is inconsistent"
                    )

                ExecutionTrackingService.mark_confirmed(
                    db,
                    execution,
                )

                call.provider_name = result.provider_name
                call.provider_call_id = result.provider_call_id

                StateMachine.transition_call(
                    call,
                    CallStatus.INITIATED,
                )

                StateMachine.transition_agent(
                    agent,
                    AgentStatus.DIALING,
                )

                borrower.attempt_count += 1

                return {
                    "success": True,
                    "outcome": "CONFIRMED",
                    "call_id": str(call.id),
                    "provider": result.provider_name,
                    "provider_call_id": result.provider_call_id,
                    "call_status": call.status.value,
                    "agent_status": agent.status.value,
                }

        except Exception:
            db.rollback()
            raise