
import math

from dataclasses import dataclass
from enum import Enum


class SafetyDecision(str, Enum):
    APPROVE = "APPROVE"
    REDUCE = "REDUCE"
    REJECT = "REJECT"
    FALLBACK_PROGRESSIVE = "FALLBACK_PROGRESSIVE"


@dataclass
class SafetyInput:

    requested_calls: int
    available_agents: int
    active_calls: int
    campaign_max_concurrent_calls: int

    predicted_abandoned_rate: float
    max_abandoned_rate: float

    provider_healthy: bool
    predictive_mode: bool = True

    predicted_answer_rate: float = 0.40
    ringing_calls: int = 0
    connected_calls: int = 0

    average_call_duration: float = 120
    average_setup_time: float = 5

    target_agent_occupancy: float = 0.85


@dataclass
class SafetyResult:

    decision: SafetyDecision
    approved_calls: int
    reason: str


class SafetyController:

    @staticmethod
    def evaluate(data: SafetyInput) -> SafetyResult:

        # --------------------------------
        # INPUT VALIDATION
        # --------------------------------

        if min(
            data.requested_calls,
            data.available_agents,
            data.active_calls,
            data.campaign_max_concurrent_calls,
            data.ringing_calls,
            data.connected_calls,
        ) < 0:
            raise ValueError("Counts cannot be negative")

        if data.ringing_calls > data.active_calls:
            raise ValueError("Ringing calls cannot exceed active calls")

        if not 0 <= data.predicted_abandoned_rate <= 1:
            raise ValueError("Invalid abandoned rate")

        if not 0 <= data.max_abandoned_rate <= 1:
            raise ValueError("Invalid maximum abandoned rate")

        if not 0 <= data.predicted_answer_rate <= 1:
            raise ValueError(
                "Predicted answer rate must be between 0 and 1"
            )

        if data.average_call_duration <= 0:
            raise ValueError("Average call duration must be positive")

        if data.average_setup_time <= 0:
            raise ValueError("Average setup time must be positive")

        if not 0 < data.target_agent_occupancy <= 1:
            raise ValueError("Target occupancy must be between 0 and 1")

        # --------------------------------
        # NO CALLS REQUESTED
        # --------------------------------

        if data.requested_calls == 0:
            return SafetyResult(
                SafetyDecision.APPROVE,
                0,
                "No additional calls requested.",
            )

        # --------------------------------
        # PROVIDER HEALTH PROTECTION
        # --------------------------------

        if not data.provider_healthy:

            if data.predictive_mode:
                return SafetyResult(
                    SafetyDecision.FALLBACK_PROGRESSIVE,
                    0,
                    "Provider unhealthy. Predictive dialing suspended.",
                )

            return SafetyResult(
                SafetyDecision.REJECT,
                0,
                "Provider unhealthy. Outbound dialing blocked.",
            )

        # --------------------------------
        # ANSWER RATE VALIDATION
        # --------------------------------

        if (
            data.predictive_mode
            and data.predicted_answer_rate == 0
        ):
            return SafetyResult(
                SafetyDecision.REJECT,
                0,
                "No reliable answer-rate estimate available.",
            )

        # --------------------------------
        # ABANDONED-CALL PROTECTION
        # --------------------------------

        if (
            data.predicted_abandoned_rate
            > data.max_abandoned_rate
        ):
            return SafetyResult(
                SafetyDecision.REJECT,
                0,
                "Predicted abandoned-call rate exceeds campaign limit.",
            )

        # --------------------------------
        # CAMPAIGN CAPACITY
        # --------------------------------

        campaign_capacity = max(
            0,
            data.campaign_max_concurrent_calls
            - data.active_calls,
        )

        if campaign_capacity == 0:
            return SafetyResult(
                SafetyDecision.REJECT,
                0,
                "Campaign concurrency limit reached.",
            )

        # --------------------------------
        # PROGRESSIVE DIALING
        # --------------------------------

        if not data.predictive_mode:

            safe_capacity = min(
                data.available_agents,
                campaign_capacity,
            )

        # --------------------------------
        # PREDICTIVE DIALING
        # --------------------------------

        else:

            completion_probability = min(
                1.0,
                data.average_setup_time
                / data.average_call_duration,
            )

            projected_agents = (
                data.available_agents
                + data.connected_calls * completion_probability
            )

            safe_answer_capacity = (
                projected_agents
                * data.target_agent_occupancy
            )

            expected_existing_answers = (
                data.ringing_calls
                * data.predicted_answer_rate
            )

            remaining_answer_capacity = max(
                0,
                safe_answer_capacity
                - expected_existing_answers,
            )

            safe_capacity = math.floor(
                remaining_answer_capacity
                / data.predicted_answer_rate
            )

            safe_capacity = min(
                safe_capacity,
                campaign_capacity,
            )

        # --------------------------------
        # FINAL SAFETY DECISION
        # --------------------------------

        if safe_capacity <= 0:
            return SafetyResult(
                SafetyDecision.REJECT,
                0,
                "No safe dialing capacity available.",
            )

        approved_calls = min(
            data.requested_calls,
            safe_capacity,
        )

        if approved_calls < data.requested_calls:
            return SafetyResult(
                SafetyDecision.REDUCE,
                approved_calls,
                "Requested dialing volume exceeds independent safety capacity.",
            )

        return SafetyResult(
            SafetyDecision.APPROVE,
            approved_calls,
            "Requested dialing volume satisfies safety constraints.",
        )
