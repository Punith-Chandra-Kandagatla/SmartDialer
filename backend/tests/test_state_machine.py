import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from app.models.agent import Agent
from app.models.call import Call
from app.models.enums import AgentStatus, CallStatus
from app.services.state_machine import (
    StateMachine,
    InvalidTransitionError,
)


def create_agent(status):
    return Agent(
        name="Test Agent",
        email=f"{uuid.uuid4().hex}@test.local",
        status=status,
    )


def create_call(status):
    return Call(
        idempotency_key=str(uuid.uuid4()),
        campaign_id=uuid.uuid4(),
        borrower_id=uuid.uuid4(),
        status=status,
        attempt_number=1,
    )


def test_valid_agent_transitions():

    agent = create_agent(AgentStatus.OFFLINE)

    assert StateMachine.transition_agent(
        agent, AgentStatus.AVAILABLE
    )

    assert agent.status == AgentStatus.AVAILABLE

    assert StateMachine.transition_agent(
        agent, AgentStatus.RESERVED
    )

    assert agent.status == AgentStatus.RESERVED

    print("Valid agent transitions: PASSED")


def test_invalid_agent_transition():

    agent = create_agent(AgentStatus.OFFLINE)

    with pytest.raises(InvalidTransitionError):
        StateMachine.transition_agent(
            agent, AgentStatus.CONNECTED
        )

    assert agent.status == AgentStatus.OFFLINE

    print("Invalid agent transition protection: PASSED")


def test_duplicate_agent_transition():

    agent = create_agent(AgentStatus.AVAILABLE)

    result = StateMachine.transition_agent(
        agent, AgentStatus.AVAILABLE
    )

    assert result is False

    print("Duplicate agent transition protection: PASSED")


def test_valid_call_lifecycle():

    call = create_call(CallStatus.QUEUED)

    transitions = [
        CallStatus.RESERVED,
        CallStatus.INITIATED,
        CallStatus.RINGING,
        CallStatus.ANSWERED,
        CallStatus.CONNECTED,
        CallStatus.COMPLETED,
    ]

    for status in transitions:
        assert StateMachine.transition_call(call, status)

    assert call.status == CallStatus.COMPLETED
    assert call.initiated_at is not None
    assert call.answered_at is not None
    assert call.connected_at is not None
    assert call.completed_at is not None

    print("Complete call lifecycle: PASSED")


def test_out_of_order_provider_event():

    call = create_call(CallStatus.INITIATED)

    # Provider reports ANSWERED before RINGING
    assert StateMachine.transition_call(
        call, CallStatus.ANSWERED
    )

    assert call.status == CallStatus.ANSWERED

    print("Out-of-order event handling: PASSED")


def test_invalid_call_transition():

    call = create_call(CallStatus.QUEUED)

    with pytest.raises(InvalidTransitionError):
        StateMachine.transition_call(
            call, CallStatus.CONNECTED
        )

    assert call.status == CallStatus.QUEUED

    print("Invalid call transition protection: PASSED")


def test_duplicate_call_transition():

    call = create_call(CallStatus.INITIATED)

    result = StateMachine.transition_call(
        call, CallStatus.INITIATED
    )

    assert result is False

    print("Duplicate call transition protection: PASSED")


def test_terminal_call_state():

    call = create_call(CallStatus.COMPLETED)

    with pytest.raises(InvalidTransitionError):
        StateMachine.transition_call(
            call, CallStatus.RINGING
        )

    assert call.status == CallStatus.COMPLETED

    print("Terminal state protection: PASSED")


if __name__ == "__main__":

    test_valid_agent_transitions()
    test_invalid_agent_transition()
    test_duplicate_agent_transition()
    test_valid_call_lifecycle()
    test_out_of_order_provider_event()
    test_invalid_call_transition()
    test_duplicate_call_transition()
    test_terminal_call_state()

    print("\nALL STATE MACHINE TESTS PASSED!")