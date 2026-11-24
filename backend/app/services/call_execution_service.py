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


class CallExecutionService:

    @staticmethod
    def execute_call(
        db: Session,
        call_id: uuid.UUID,
        provider_manager: ProviderManager,
    ) -> dict:

        # PHASE 1: Persist execution intent before external request.

        try:
            call = db.execute(
                select(Call)
                .where(Call.id == call_id)
                .with_for_update()
            ).scalar_one_or_none()

            if call is None:
                raise ValueError("Call not found")

            execution = ExecutionTrackingService.get_or_create(
                db,
                call_id,
            )

            if execution.status == ExecutionStatus.CONFIRMED:
                return {
                    "success": True,
                    "duplicate": True,
                    "provider_call_id": call.provider_call_id,
                    "status": execution.status.value,
                }

            if execution.status != ExecutionStatus.NOT_STARTED:
                raise ValueError(
                    f"Execution cannot be retried automatically: "
                    f"{execution.status.value}"
                )

            if call.status != CallStatus.RESERVED:
                raise ValueError(
                    "Only reserved calls can be executed"
                )

            agent = db.execute(
                select(Agent)
                .where(Agent.id == call.agent_id)
                .with_for_update()
            ).scalar_one_or_none()

            borrower = db.execute(
                select(Borrower)
                .where(Borrower.id == call.borrower_id)
                .with_for_update()
            ).scalar_one_or_none()

            if (
                agent is None
                or agent.status != AgentStatus.RESERVED
                or agent.reservation_token != call.reservation_token
            ):
                raise ValueError("Agent reservation is invalid")

            if (
                borrower is None
                or borrower.status != BorrowerStatus.IN_PROGRESS
                or borrower.reservation_token != call.reservation_token
            ):
                raise ValueError("Borrower reservation is invalid")

            if (
                agent.reserved_until is None
                or borrower.reserved_until is None
            ):
                raise ValueError("Reservation lease is missing")

            provider = provider_manager.select_healthy_provider()

            if provider is None:
                raise RuntimeError(
                    "No healthy telecom provider available"
                )

            ExecutionTrackingService.mark_requesting(
                db,
                execution,
                provider.provider_name,
            )

            provider_name = provider.provider_name
            phone_number = borrower.phone_number
            idempotency_key = call.idempotency_key

            # Commit before making the external provider request.
            db.commit()

        except Exception:
            db.rollback()
            raise

        # PHASE 2: Make the external request outside the DB transaction.

        try:
            result = provider.initiate_call(
                phone_number=phone_number,
                idempotency_key=idempotency_key,
            )

        except Exception as exc:

            # A timeout or connection failure may mean that
            # the provider accepted the call but the response was lost.
            with db.begin():

                execution = db.execute(
                    select(CallExecution)
                    .where(CallExecution.call_id == call_id)
                    .with_for_update()
                ).scalar_one()

                if execution.status == ExecutionStatus.REQUESTING:

                    ExecutionTrackingService.mark_unknown(
                        db,
                        execution,
                        str(exc),
                    )

            return {
                "success": False,
                "outcome": "UNKNOWN",
                "call_id": str(call_id),
                "reason": str(exc),
                "retry_allowed": False,
            }

        # PHASE 3: Persist provider response.

        try:
            with db.begin():

                call = db.execute(
                    select(Call)
                    .where(Call.id == call_id)
                    .with_for_update()
                ).scalar_one()

                execution = db.execute(
                    select(CallExecution)
                    .where(CallExecution.call_id == call_id)
                    .with_for_update()
                ).scalar_one()

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

                if execution.status != ExecutionStatus.REQUESTING:
                    raise ValueError(
                        "Execution state changed while provider request was running"
                    )

                if result.success:

                    ExecutionTrackingService.mark_confirmed(
                        db,
                        execution,
                    )

                    StateMachine.transition_call(
                        call,
                        CallStatus.INITIATED,
                    )

                    StateMachine.transition_agent(
                        agent,
                        AgentStatus.DIALING,
                    )

                    call.provider_name = result.provider_name
                    call.provider_call_id = result.provider_call_id

                    borrower.attempt_count += 1

                    return {
                        "success": True,
                        "call_id": str(call.id),
                        "provider": result.provider_name,
                        "provider_call_id": result.provider_call_id,
                        "status": call.status.value,
                        "execution_status": execution.status.value,
                    }

                # A definitive provider rejection.
                ExecutionTrackingService.mark_failed(
                    db,
                    execution,
                    result.error_message or "Provider rejected call",
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
                    "success": False,
                    "call_id": str(call.id),
                    "execution_status": execution.status.value,
                    "reason": result.error_message,
                }

        except Exception:
            db.rollback()
            raise