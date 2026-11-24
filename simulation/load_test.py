import time

from app.services.predictive_engine import PredictivePacingEngine, PacingInput
from app.services.safety_controller import SafetyController, SafetyInput


def benchmark(agent_count):
    iterations = 1000
    start = time.perf_counter()

    for _ in range(iterations):
        recommendation = PredictivePacingEngine.recommend(
            PacingInput(
                available_agents=agent_count,
                active_calls=0,
                ringing_calls=0,
                connected_calls=0,
                historical_answer_rate=0.5,
                historical_call_count=200,
                average_call_duration=120,
                average_setup_time=5,
                campaign_max_concurrent_calls=agent_count * 2,
                provider_healthy=True,
            )
        )

        SafetyController.evaluate(
            SafetyInput(
                requested_calls=recommendation.recommended_calls,
                available_agents=agent_count,
                active_calls=0,
                campaign_max_concurrent_calls=agent_count * 2,
                predicted_abandoned_rate=0.0,
                max_abandoned_rate=0.03,
                provider_healthy=True,
                predictive_mode=True,
                predicted_answer_rate=recommendation.effective_answer_rate,
            )
        )

    elapsed = time.perf_counter() - start

    print(f"\nAgents: {agent_count:,}")
    print(f"Iterations: {iterations:,}")
    print(f"Total time: {elapsed:.4f} seconds")
    print(f"Decisions/sec: {iterations / elapsed:,.2f}")


if __name__ == "__main__":
    print("SMARTDIALER — PACING ENGINE LOAD TEST")

    for count in [100, 1000, 10000]:
        benchmark(count)