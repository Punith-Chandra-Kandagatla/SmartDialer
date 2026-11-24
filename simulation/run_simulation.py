from dataclasses import asdict

from app.services.predictive_engine import (
    PredictivePacingEngine,
    PacingInput,
)

from app.services.safety_controller import (
    SafetyController,
    SafetyInput,
)


SCENARIOS = [
    {
        "name": "LOW ANSWER RATE",
        "answer_rate": 0.20,
        "call_duration": 120,
    },
    {
        "name": "MEDIUM ANSWER RATE",
        "answer_rate": 0.50,
        "call_duration": 90,
    },
    {
        "name": "HIGH ANSWER RATE",
        "answer_rate": 0.70,
        "call_duration": 180,
    },
]


def run_scenario(scenario):

    agents = 100
    max_calls = 200
    answer_rate = scenario["answer_rate"]

    print("\n" + "=" * 65)
    print(f"SCENARIO: {scenario['name']}")
    print("=" * 65)

    pacing_input = PacingInput(
        available_agents=agents,
        active_calls=0,
        ringing_calls=0,
        connected_calls=0,
        historical_answer_rate=answer_rate,
        historical_call_count=200,
        average_call_duration=scenario["call_duration"],
        average_setup_time=5,
        campaign_max_concurrent_calls=max_calls,
        provider_healthy=True,
        target_agent_occupancy=0.85,
        pacing_factor=1.0,
    )

    recommendation = PredictivePacingEngine.recommend(
        pacing_input
    )

    print("\nPREDICTIVE ENGINE")
    print("-" * 40)

    recommendation_data = asdict(recommendation)

    for key, value in recommendation_data.items():
        print(f"{key}: {value}")

    requested_calls = recommendation_data.get(
        "recommended_calls",
        recommendation_data.get("requested_calls", 0),
    )

    expected_answers = requested_calls * answer_rate

    predicted_abandonment = (
        max(0, expected_answers - agents)
        / max(expected_answers, 1)
    )

    safety_input = SafetyInput(
        requested_calls=int(requested_calls),
        available_agents=agents,
        active_calls=0,
        campaign_max_concurrent_calls=max_calls,
        predicted_abandoned_rate=predicted_abandonment,
        max_abandoned_rate=0.03,
        provider_healthy=True,
        predictive_mode=True,
        predicted_answer_rate=answer_rate,
        ringing_calls=0,
        connected_calls=0,
        average_call_duration=scenario["call_duration"],
        average_setup_time=5,
        target_agent_occupancy=0.85,
    )

    safety_result = SafetyController.evaluate(safety_input)

    print("\nSAFETY CONTROLLER")
    print("-" * 40)

    for key, value in asdict(safety_result).items():
        print(f"{key}: {value}")

    print("\nSCENARIO SUMMARY")
    print("-" * 40)
    print(f"Available agents:       {agents}")
    print(f"Historical answer rate: {answer_rate:.0%}")
    print(f"Average call duration:  {scenario['call_duration']} sec")
    print(f"Requested calls:        {requested_calls}")
    print(f"Expected answers:       {expected_answers:.1f}")
    print(f"Estimated abandonment:  {predicted_abandonment:.2%}")

def run_answer_rate_shock():

    print("\n" + "=" * 65)
    print("SIGNATURE DEMO: 70% TO 10% ANSWER-RATE SHOCK")
    print("=" * 65)

    for rate in [0.70, 0.10]:

        print(f"\nLIVE ANSWER RATE: {rate:.0%}")

        data = PacingInput(
            available_agents=100,
            active_calls=0,
            ringing_calls=0,
            connected_calls=0,
            historical_answer_rate=rate,
            historical_call_count=200,
            average_call_duration=120,
            average_setup_time=5,
            campaign_max_concurrent_calls=200,
            provider_healthy=True,
        )

        recommendation = PredictivePacingEngine.recommend(data)

        print(f"Recommended calls: {recommendation.recommended_calls}")
        print(f"Effective answer rate: {recommendation.effective_answer_rate:.2%}")
        print(f"Confidence: {recommendation.confidence:.2%}")

        safety = SafetyController.evaluate(
            SafetyInput(
                requested_calls=recommendation.recommended_calls,
                available_agents=100,
                active_calls=0,
                campaign_max_concurrent_calls=200,
                predicted_abandoned_rate=0.0,
                max_abandoned_rate=0.03,
                provider_healthy=True,
                predictive_mode=True,
                predicted_answer_rate=recommendation.effective_answer_rate,
            )
        )

        print(f"Safety decision: {safety.decision.value}")
        print(f"Approved calls: {safety.approved_calls}")
        print(f"Safety reason: {safety.reason}")



def main():

    print("\nSMARTDIALER — PREDICTIVE SIMULATION")
    print("Testing adaptive pacing and independent safety controls")

    for scenario in SCENARIOS:
        run_scenario(scenario)
    run_answer_rate_shock()
    print("\n" + "=" * 65)
    print("ALL SIMULATION SCENARIOS COMPLETED")
    print("=" * 65)


if __name__ == "__main__":
    main()