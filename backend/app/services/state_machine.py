from datetime import datetime, timezone

from app.models.agent import Agent
from app.models.call import Call
from app.models.enums import AgentStatus, CallStatus


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is requested."""
    pass


class StateMachine:

    # ----------------------------------
    # AGENT STATE TRANSITIONS
    # ----------------------------------

    AGENT_TRANSITIONS = {
        AgentStatus.OFFLINE: {
            AgentStatus.AVAILABLE,
        },

        AgentStatus.AVAILABLE: {
            AgentStatus.RESERVED,
            AgentStatus.OFFLINE,
            AgentStatus.PAUSED,
        },

        AgentStatus.RESERVED: {
            AgentStatus.AVAILABLE,
            AgentStatus.DIALING,
            AgentStatus.OFFLINE,
        },

        AgentStatus.DIALING: {
            AgentStatus.CONNECTED,
            AgentStatus.AVAILABLE,
            AgentStatus.WRAP_UP,
            AgentStatus.OFFLINE,
        },

        AgentStatus.CONNECTED: {
            AgentStatus.WRAP_UP,
            AgentStatus.OFFLINE,
        },

        AgentStatus.WRAP_UP: {
            AgentStatus.AVAILABLE,
            AgentStatus.PAUSED,
            AgentStatus.OFFLINE,
        },

        AgentStatus.PAUSED: {
            AgentStatus.AVAILABLE,
            AgentStatus.OFFLINE,
        },
    }

    # ----------------------------------
    # CALL STATE TRANSITIONS
    # ----------------------------------

    CALL_TRANSITIONS = {
        CallStatus.QUEUED: {
            CallStatus.RESERVED,
            CallStatus.CANCELLED,
        },

        CallStatus.RESERVED: {
            CallStatus.INITIATED,
            CallStatus.CANCELLED,
            CallStatus.FAILED,
        },

        CallStatus.INITIATED: {
            CallStatus.RINGING,
            CallStatus.ANSWERED,
            CallStatus.FAILED,
            CallStatus.CANCELLED,
        },

        CallStatus.RINGING: {
            CallStatus.ANSWERED,
            CallStatus.FAILED,
            CallStatus.CANCELLED,
        },

        CallStatus.ANSWERED: {
            CallStatus.CONNECTED,
            CallStatus.FAILED,
        },

        CallStatus.CONNECTED: {
            CallStatus.COMPLETED,
            CallStatus.FAILED,
        },

        CallStatus.COMPLETED: set(),
        CallStatus.FAILED: set(),
        CallStatus.CANCELLED: set(),
    }

    @staticmethod
    def transition_agent(
        agent: Agent,
        new_status: AgentStatus,
    ) -> bool:
        """
        Validate and apply an agent state transition.

        Returns False for duplicate transitions.
        Raises InvalidTransitionError for invalid transitions.
        """

        current_status = agent.status

        if current_status == new_status:
            return False

        allowed_transitions = (
            StateMachine.AGENT_TRANSITIONS.get(current_status, set())
        )

        if new_status not in allowed_transitions:
            raise InvalidTransitionError(
                f"Invalid agent transition: "
                f"{current_status.value} -> {new_status.value}"
            )

        agent.status = new_status
        agent.updated_at = datetime.now(timezone.utc)

        return True

    @staticmethod
    def transition_call(
        call: Call,
        new_status: CallStatus,
        failure_reason: str | None = None,
    ) -> bool:
        """
        Validate and apply a call state transition.

        Updates lifecycle timestamps automatically.
        Returns False for duplicate transitions.
        Raises InvalidTransitionError for invalid transitions.
        """

        current_status = call.status

        if current_status == new_status:
            return False

        allowed_transitions = (
            StateMachine.CALL_TRANSITIONS.get(current_status, set())
        )

        if new_status not in allowed_transitions:
            raise InvalidTransitionError(
                f"Invalid call transition: "
                f"{current_status.value} -> {new_status.value}"
            )

        now = datetime.now(timezone.utc)

        call.status = new_status
        call.updated_at = now

        if new_status == CallStatus.INITIATED:
            call.initiated_at = now

        elif new_status == CallStatus.ANSWERED:
            call.answered_at = now

        elif new_status == CallStatus.CONNECTED:
            call.connected_at = now

        elif new_status in {
            CallStatus.COMPLETED,
            CallStatus.FAILED,
            CallStatus.CANCELLED,
        }:
            call.completed_at = now

        if new_status == CallStatus.FAILED:
            call.failure_reason = failure_reason or "Call failed"

        elif failure_reason is not None:
            raise ValueError(
                "failure_reason can only be provided for FAILED calls"
            )

        return True