
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from app.services.safety_controller import (
    SafetyController,
    SafetyInput,
    SafetyDecision,
)


def create_input(**overrides):

    data = {
        "requested_calls": 30,
        "available_agents": 20,
        "active_calls": 10,
        "campaign_max_concurrent_calls": 50,
        "predicted_abandoned_rate": 0.01,
        "max_abandoned_rate": 0.03,
        "provider_healthy": True,
        "predictive_mode": True,
        "predicted_answer_rate": 0.40,
        "ringing_calls": 3,
        "connected_calls": 7,
        "average_call_duration": 120,
        "average_setup_time": 5,
        "target_agent_occupancy": 0.85,
    }

    data.update(overrides)

    return SafetyInput(**data)


def test_predictive_mode_allows_more_calls_than_agents():

    result = SafetyController.evaluate(
        create_input(
            requested_calls=30,
        )
    )

    assert result.decision == SafetyDecision.APPROVE
    assert result.approved_calls == 30
    assert result.approved_calls > 20

    print("Predictive dialing capacity: PASSED")


def test_progressive_mode_limits_calls_to_agents():

    result = SafetyController.evaluate(
        create_input(
            requested_calls=30,
            predictive_mode=False,
            available_agents=20,
        )
    )

    assert result.decision == SafetyDecision.REDUCE
    assert result.approved_calls == 20

    print("Progressive dialing capacity: PASSED")


def test_excessive_abandoned_rate():

    result = SafetyController.evaluate(
        create_input(
            predicted_abandoned_rate=0.08,
        )
    )

    assert result.decision == SafetyDecision.REJECT
    assert result.approved_calls == 0

    print("Abandoned-call protection: PASSED")


def test_unhealthy_provider_predictive_fallback():

    result = SafetyController.evaluate(
        create_input(provider_healthy=False)
    )

    assert result.decision == SafetyDecision.FALLBACK_PROGRESSIVE
    assert result.approved_calls == 0

    print("Predictive provider fallback: PASSED")


def test_unhealthy_provider_progressive_rejection():

    result = SafetyController.evaluate(
        create_input(
            provider_healthy=False,
            predictive_mode=False,
        )
    )

    assert result.decision == SafetyDecision.REJECT
    assert result.approved_calls == 0

    print("Progressive provider rejection: PASSED")


def test_no_available_agents():

    result = SafetyController.evaluate(
        create_input(
            available_agents=0,
            connected_calls=0,
        )
    )

    assert result.decision == SafetyDecision.REJECT
    assert result.approved_calls == 0

    print("Agent availability protection: PASSED")


def test_campaign_capacity():

    result = SafetyController.evaluate(
        create_input(
            requested_calls=30,
            active_calls=45,
            campaign_max_concurrent_calls=50,
        )
    )

    assert result.decision == SafetyDecision.REDUCE
    assert result.approved_calls == 5

    print("Campaign concurrency protection: PASSED")


def test_zero_calls_requested():

    result = SafetyController.evaluate(
        create_input(requested_calls=0)
    )

    assert result.decision == SafetyDecision.APPROVE
    assert result.approved_calls == 0

    print("Zero-call handling: PASSED")


def test_invalid_abandoned_rate():

    with pytest.raises(ValueError):

        SafetyController.evaluate(
            create_input(predicted_abandoned_rate=1.5)
        )

    print("Invalid abandoned-rate validation: PASSED")


def test_invalid_answer_rate():

    with pytest.raises(ValueError):

        SafetyController.evaluate(
            create_input(predicted_answer_rate=-0.1)
        )

    print("Invalid answer-rate validation: PASSED")


if __name__ == "__main__":

    test_predictive_mode_allows_more_calls_than_agents()
    test_progressive_mode_limits_calls_to_agents()
    test_excessive_abandoned_rate()
    test_unhealthy_provider_predictive_fallback()
    test_unhealthy_provider_progressive_rejection()
    test_no_available_agents()
    test_campaign_capacity()
    test_zero_calls_requested()
    test_invalid_abandoned_rate()
    test_invalid_answer_rate()

    print("\nALL UPDATED SAFETY CONTROLLER TESTS PASSED!")
