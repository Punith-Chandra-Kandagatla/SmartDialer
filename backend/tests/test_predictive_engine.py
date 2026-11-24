import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from app.services.predictive_engine import (
    PredictivePacingEngine,
    PacingInput,
)


def create_input(**overrides):

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


def test_normal_pacing():

    result = PredictivePacingEngine.recommend(
        create_input()
    )

    assert result.recommended_calls > 0
    assert 0 <= result.effective_answer_rate <= 1
    assert 0 <= result.confidence <= 1

    print("Normal predictive pacing: PASSED")


def test_low_answer_rate():

    result = PredictivePacingEngine.recommend(
        create_input(
            historical_answer_rate=0.20,
            historical_call_count=100,
        )
    )

    assert result.recommended_calls > 0

    print("Low answer-rate scenario: PASSED")


def test_high_answer_rate():

    result = PredictivePacingEngine.recommend(
        create_input(
            historical_answer_rate=0.70,
            historical_call_count=100,
        )
    )

    assert result.recommended_calls > 0

    print("High answer-rate scenario: PASSED")


def test_provider_unhealthy():

    result = PredictivePacingEngine.recommend(
        create_input(provider_healthy=False)
    )

    assert result.recommended_calls == 0
    assert result.confidence == 0

    print("Provider health protection: PASSED")


def test_campaign_capacity_reached():

    result = PredictivePacingEngine.recommend(
        create_input(
            active_calls=50,
            ringing_calls=10,
            connected_calls=40,
            campaign_max_concurrent_calls=50,
        )
    )

    assert result.recommended_calls == 0

    print("Campaign capacity protection: PASSED")


def test_confidence_increases_with_sample_size():

    small_sample = PredictivePacingEngine.recommend(
        create_input(historical_call_count=10)
    )

    large_sample = PredictivePacingEngine.recommend(
        create_input(historical_call_count=1000)
    )

    assert large_sample.confidence > small_sample.confidence

    print("Confidence-aware estimation: PASSED")


def test_more_connected_agents():

    normal = PredictivePacingEngine.recommend(
        create_input(connected_calls=5)
    )

    more_connected = PredictivePacingEngine.recommend(
        create_input(connected_calls=15)
    )

    assert more_connected.recommended_calls >= normal.recommended_calls

    print("Connected-agent capacity projection: PASSED")


def test_invalid_answer_rate():

    with pytest.raises(ValueError):

        PredictivePacingEngine.recommend(
            create_input(historical_answer_rate=1.5)
        )

    print("Invalid answer-rate validation: PASSED")


def test_invalid_call_duration():

    with pytest.raises(ValueError):

        PredictivePacingEngine.recommend(
            create_input(average_call_duration=0)
        )

    print("Invalid call-duration validation: PASSED")


if __name__ == "__main__":

    test_normal_pacing()
    test_low_answer_rate()
    test_high_answer_rate()
    test_provider_unhealthy()
    test_campaign_capacity_reached()
    test_confidence_increases_with_sample_size()
    test_more_connected_agents()
    test_invalid_answer_rate()
    test_invalid_call_duration()

    print("\nALL PREDICTIVE ENGINE TESTS PASSED!")
