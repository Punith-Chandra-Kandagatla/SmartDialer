
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.predictive_engine import PacingInput
from app.services.dialing_orchestrator import DialingOrchestrator


def create_pacing_input(**overrides):

    data = {
        "available_agents": 20,
        "active_calls": 10,
        "ringing_calls": 3,
        "connected_calls": 7,
        "historical_answer_rate": 0.40,
        "historical_call_count": 100,
        "average_call_duration": 120,
        "average_setup_time": 5,
        "campaign_max_concurrent_calls": 50,
        "provider_healthy": True,
        "target_agent_occupancy": 0.85,
        "pacing_factor": 1.0,
    }

    data.update(overrides)

    return PacingInput(**data)


def test_predictive_recommendation_and_approval():

    result = DialingOrchestrator.evaluate_predictive_dialing(
        pacing_data=create_pacing_input(),
        predicted_abandoned_rate=0.01,
        max_abandoned_rate=0.03,
    )

    assert result.recommended_calls > 0
    assert result.approved_calls >= 0
    assert result.approved_calls <= result.recommended_calls

    print("Predictive recommendation and safety approval: PASSED")


def test_safety_controller_rejects_high_abandonment_risk():

    result = DialingOrchestrator.evaluate_predictive_dialing(
        pacing_data=create_pacing_input(),
        predicted_abandoned_rate=0.10,
        max_abandoned_rate=0.03,
    )

    assert result.approved_calls == 0
    assert result.final_decision == "REJECT"

    print("Independent safety rejection: PASSED")


def test_provider_failure_stops_predictive_dialing():

    result = DialingOrchestrator.evaluate_predictive_dialing(
        pacing_data=create_pacing_input(
            provider_healthy=False
        ),
        predicted_abandoned_rate=0.01,
        max_abandoned_rate=0.03,
    )

    assert result.recommended_calls == 0
    assert result.approved_calls == 0

    print("Provider failure protection: PASSED")


def test_campaign_limit_is_respected():

    result = DialingOrchestrator.evaluate_predictive_dialing(
        pacing_data=create_pacing_input(
            active_calls=45,
            campaign_max_concurrent_calls=50,
        ),
        predicted_abandoned_rate=0.01,
        max_abandoned_rate=0.03,
    )

    assert result.approved_calls <= 5

    print("Campaign concurrency protection: PASSED")


def test_decision_explanation():

    result = DialingOrchestrator.evaluate_predictive_dialing(
        pacing_data=create_pacing_input(),
        predicted_abandoned_rate=0.01,
        max_abandoned_rate=0.03,
    )

    assert result.explanation
    assert "recommended" in result.explanation
    assert "approved" in result.explanation

    print("Decision explainability: PASSED")


if __name__ == "__main__":

    test_predictive_recommendation_and_approval()
    test_safety_controller_rejects_high_abandonment_risk()
    test_provider_failure_stops_predictive_dialing()
    test_campaign_limit_is_respected()
    test_decision_explanation()

    print("\nALL DIALING ORCHESTRATOR TESTS PASSED!")
