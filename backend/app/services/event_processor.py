import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.borrower import Borrower
from app.models.call import Call
from app.models.provider_event import ProviderEvent

from app.models.enums import (
    AgentStatus,
    BorrowerStatus,
    CallStatus,
    ProviderEventStatus,
)

from app.services.state_machine import (
    StateMachine,
    InvalidTransitionError,
)


class EventProcessor:

    EVENT_TRANSITIONS = {
        "INITIATED": CallStatus.INITIATED,
        "RINGING": CallStatus.RINGING,
        "ANSWERED": CallStatus.ANSWERED,
        "CONNECTED": CallStatus.CONNECTED,
        "COMPLETED": CallStatus.COMPLETED,
        "FAILED": CallStatus.FAILED,
    }

    EVENT_ORDER = {
        CallStatus.INITIATED: 1,
        CallStatus.RINGING: 2,
        CallStatus.ANSWERED: 3,
        CallStatus.CONNECTED: 4,
        CallStatus.COMPLETED: 5,
    }

    @staticmethod
    def process_event(
        db: Session,
        provider_name: str,
        provider_event_id: str,
        provider_call_id: str,
        event_type: str,
        payload: dict,
    ) -> dict:

        event_type = event_type.upper()

        if event_type not in EventProcessor.EVENT_TRANSITIONS:
            return {
                "success": False,
                "reason": "Unsupported provider event",
            }

        # Find and lock the corresponding call
        call = db.execute(
            select(Call)
            .where(
                Call.provider_name == provider_name,
                Call.provider_call_id == provider_call_id,
            )
            .with_for_update()
        ).scalar_one_or_none()

        if call is None:
            return {
                "success": False,
                "reason": "Unknown provider call ID",
            }

        # Record event using a savepoint.
        # Duplicate events must not invalidate the outer transaction.
        try:
            with db.begin_nested():

                event = ProviderEvent(
                    call_id=call.id,
                    provider_name=provider_name,
                    provider_event_id=provider_event_id,
                    event_type=event_type,
                    processing_status=ProviderEventStatus.RECEIVED,
                    payload=payload,
                )

                db.add(event)
                db.flush()

        except IntegrityError:
            return {
                "success": True,
                "duplicate": True,
                "reason": "Event already processed or received",
            }

        # Lock associated resources
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

        if agent is None or borrower is None:
            event.processing_status = ProviderEventStatus.FAILED
            event.error_message = (
                "Associated agent or borrower not found"
            )
            event.processed_at = datetime.now(timezone.utc)

            db.commit()

            return {
                "success": False,
                "reason": event.error_message,
            }

        new_status = EventProcessor.EVENT_TRANSITIONS[event_type]

        try:

            # Reject stale events that would move the call backwards.
            current_order = EventProcessor.EVENT_ORDER.get(
                call.status, 0
            )

            new_order = EventProcessor.EVENT_ORDER.get(
                new_status, 0
            )

            if new_order < current_order:
                event.processing_status = ProviderEventStatus.FAILED
                event.error_message = (
                    f"Out-of-order event ignored: "
                    f"{new_status.value} received after "
                    f"{call.status.value}"
                )
                event.processed_at = datetime.now(timezone.utc)

                db.commit()

                return {
                    "success": False,
                    "duplicate": False,
                    "reason": event.error_message,
                    "call_status": call.status.value,
                }

            # Apply valid state transition.
            changed = StateMachine.transition_call(
                call,
                new_status,
            )

            if not changed:
                event.processing_status = ProviderEventStatus.PROCESSED
                event.processed_at = datetime.now(timezone.utc)

                db.commit()

                return {
                    "success": True,
                    "duplicate": True,
                    "call_status": call.status.value,
                    "reason": "Call is already in the requested state",
                }

            # Update agent lifecycle
            if new_status == CallStatus.CONNECTED:

                if agent.status == AgentStatus.DIALING:
                    StateMachine.transition_agent(
                        agent,
                        AgentStatus.CONNECTED,
                    )

            elif new_status == CallStatus.COMPLETED:

                if agent.status in {
                    AgentStatus.CONNECTED,
                    AgentStatus.DIALING,
                }:
                    StateMachine.transition_agent(
                        agent,
                        AgentStatus.WRAP_UP,
                    )

                borrower.status = BorrowerStatus.CONTACTED

                agent.reservation_token = None
                agent.reserved_until = None

                borrower.reservation_token = None
                borrower.reserved_until = None

            elif new_status == CallStatus.FAILED:

                if agent.status in {
                    AgentStatus.DIALING,
                    AgentStatus.CONNECTED,
                    AgentStatus.RESERVED,
                }:
                    agent.status = AgentStatus.AVAILABLE

                borrower.status = (
                    BorrowerStatus.ELIGIBLE
                    if borrower.attempt_count < borrower.max_attempts
                    else BorrowerStatus.INELIGIBLE
                )

                agent.reservation_token = None
                agent.reserved_until = None

                borrower.reservation_token = None
                borrower.reserved_until = None

            event.processing_status = ProviderEventStatus.PROCESSED
            event.processed_at = datetime.now(timezone.utc)

            db.commit()

            return {
                "success": True,
                "duplicate": False,
                "call_id": str(call.id),
                "call_status": call.status.value,
                "agent_status": agent.status.value,
                "borrower_status": borrower.status.value,
            }

        except InvalidTransitionError as exc:

            event.processing_status = ProviderEventStatus.FAILED
            event.error_message = str(exc)
            event.processed_at = datetime.now(timezone.utc)

            db.commit()

            return {
                "success": False,
                "reason": str(exc),
                "call_status": call.status.value,
            }

        except Exception:
            db.rollback()
            raise