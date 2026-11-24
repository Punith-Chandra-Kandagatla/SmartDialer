import math

from dataclasses import dataclass


@dataclass
class PacingInput:

    available_agents: int
    active_calls: int
    ringing_calls: int
    connected_calls: int

    historical_answer_rate: float
    historical_call_count: int

    average_call_duration: float
    average_setup_time: float

    campaign_max_concurrent_calls: int

    provider_healthy: bool = True

    target_agent_occupancy: float = 0.85
    pacing_factor: float = 1.0


@dataclass
class PacingRecommendation:

    recommended_calls: int
    effective_answer_rate: float
    confidence: float
    expected_answers: float
    reason: str


class PredictivePacingEngine:

    PRIOR_ANSWER_RATE = 0.40
    PRIOR_SAMPLE_SIZE = 20

    @staticmethod
    def recommend(
        data: PacingInput,
    ) -> PacingRecommendation:

        # -----------------------------
        # INPUT VALIDATION
        # -----------------------------

        if min(
            data.available_agents,
            data.active_calls,
            data.ringing_calls,
            data.connected_calls,
            data.historical_call_count,
        ) < 0:
            raise ValueError("Counts cannot be negative")

        if data.ringing_calls > data.active_calls:
            raise ValueError(
                "Ringing calls cannot exceed active calls"
            )

        if not 0 <= data.historical_answer_rate <= 1:
            raise ValueError(
                "Answer rate must be between 0 and 1"
            )

        if data.average_call_duration <= 0:
            raise ValueError(
                "Average call duration must be positive"
            )

        if data.average_setup_time <= 0:
            raise ValueError(
                "Average setup time must be positive"
            )

        if data.campaign_max_concurrent_calls <= 0:
            raise ValueError(
                "Campaign concurrency limit must be positive"
            )

        if not 0 < data.target_agent_occupancy <= 1:
            raise ValueError(
                "Target occupancy must be between 0 and 1"
            )

        if data.pacing_factor <= 0:
            raise ValueError(
                "Pacing factor must be positive"
            )

        # -----------------------------
        # PROVIDER HEALTH CHECK
        # -----------------------------

        if not data.provider_healthy:

            return PacingRecommendation(
                recommended_calls=0,
                effective_answer_rate=0,
                confidence=0,
                expected_answers=0,
                reason="Provider unhealthy. Predictive dialing suspended.",
            )

        # -----------------------------
        # CONFIDENCE-AWARE ANSWER RATE
        # -----------------------------

        observations = data.historical_call_count

        effective_answer_rate = (
            data.historical_answer_rate * observations
            + PredictivePacingEngine.PRIOR_ANSWER_RATE
            * PredictivePacingEngine.PRIOR_SAMPLE_SIZE
        ) / (
            observations
            + PredictivePacingEngine.PRIOR_SAMPLE_SIZE
        )

        confidence = (
            observations
            / (
                observations
                + PredictivePacingEngine.PRIOR_SAMPLE_SIZE
            )
        )

        # -----------------------------
        # CAMPAIGN CAPACITY
        # -----------------------------

        remaining_capacity = max(
            0,
            data.campaign_max_concurrent_calls
            - data.active_calls,
        )

        if remaining_capacity == 0:

            return PacingRecommendation(
                recommended_calls=0,
                effective_answer_rate=effective_answer_rate,
                confidence=confidence,
                expected_answers=0,
                reason="Campaign concurrency limit reached.",
            )

        if effective_answer_rate <= 0:

            return PacingRecommendation(
                recommended_calls=0,
                effective_answer_rate=0,
                confidence=confidence,
                expected_answers=0,
                reason="No reliable answer-rate estimate available.",
            )

        # -----------------------------
        # ESTIMATE FUTURE AGENT CAPACITY
        # -----------------------------

        # Estimate how many connected agents may finish
        # their calls during the provider setup interval.

        completion_probability = min(
            1.0,
            data.average_setup_time
            / data.average_call_duration,
        )

        projected_available_agents = (
            data.available_agents
            + data.connected_calls * completion_probability
        )

        target_agent_capacity = (
            projected_available_agents
            * data.target_agent_occupancy
        )

        # -----------------------------
        # ACCOUNT FOR CALLS ALREADY RINGING
        # -----------------------------

        expected_existing_answers = (
            data.ringing_calls * effective_answer_rate
        )

        expected_answer_gap = max(
            0,
            target_agent_capacity
            - expected_existing_answers,
        )

        # -----------------------------
        # PREDICTIVE DIALING RECOMMENDATION
        # -----------------------------

        required_calls = math.ceil(
            expected_answer_gap
            / effective_answer_rate
            * data.pacing_factor
        )

        recommended_calls = min(
            required_calls,
            remaining_capacity,
        )

        expected_answers = (
            recommended_calls * effective_answer_rate
        )

        return PacingRecommendation(
            recommended_calls=recommended_calls,
            effective_answer_rate=round(
                effective_answer_rate, 4
            ),
            confidence=round(confidence, 4),
            expected_answers=round(
                expected_answers, 2
            ),
            reason=(
                "Adaptive pacing recommendation calculated "
                "using answer rate, agent capacity, "
                "call duration and provider setup time."
            ),
        )
