
from dataclasses import dataclass

from app.services.predictive_engine import (
    PredictivePacingEngine,
    PacingInput,
    PacingRecommendation,
)

from app.services.safety_controller import (
    SafetyController,
    SafetyInput,
    SafetyResult,
)


@dataclass
class DialingDecision:

    pacing_recommendation: PacingRecommendation
    safety_result: SafetyResult

    recommended_calls: int
    approved_calls: int

    final_decision: str
    explanation: str


class DialingOrchestrator:

    @staticmethod
    def evaluate_predictive_dialing(
        pacing_data: PacingInput,
        predicted_abandoned_rate: float,
        max_abandoned_rate: float,
    ) -> DialingDecision:

        # Stage 1: Obtain recommendation from predictive engine
        recommendation = PredictivePacingEngine.recommend(
            pacing_data
        )

        # Stage 2: Independently evaluate the recommendation
        safety_data = SafetyInput(
            requested_calls=recommendation.recommended_calls,

            available_agents=pacing_data.available_agents,
            active_calls=pacing_data.active_calls,

            campaign_max_concurrent_calls=(
                pacing_data.campaign_max_concurrent_calls
            ),

            predicted_abandoned_rate=predicted_abandoned_rate,
            max_abandoned_rate=max_abandoned_rate,

            provider_healthy=pacing_data.provider_healthy,
            predictive_mode=True,

            predicted_answer_rate=(
                recommendation.effective_answer_rate
            ),

            ringing_calls=pacing_data.ringing_calls,
            connected_calls=pacing_data.connected_calls,

            average_call_duration=(
                pacing_data.average_call_duration
            ),

            average_setup_time=(
                pacing_data.average_setup_time
            ),

            target_agent_occupancy=(
                pacing_data.target_agent_occupancy
            ),
        )

        safety_result = SafetyController.evaluate(
            safety_data
        )

        # Stage 3: Produce the final decision
        return DialingDecision(
            pacing_recommendation=recommendation,
            safety_result=safety_result,

            recommended_calls=recommendation.recommended_calls,
            approved_calls=safety_result.approved_calls,

            final_decision=safety_result.decision.value,

            explanation=(
                f"Predictive engine recommended "
                f"{recommendation.recommended_calls} calls. "
                f"Safety controller approved "
                f"{safety_result.approved_calls} calls. "
                f"Reason: {safety_result.reason}"
            ),
        )
