import time
import uuid

from app.providers.base import (
    BaseTelecomProvider,
    ProviderCallResult,
    ProviderHealth,
)


class ReliableMockProvider(BaseTelecomProvider):

    def __init__(self):
        self.total_calls = 0
        self.failed_calls = 0
        self.latency_ms = 100

        # Simulates provider-side idempotency.
        self.idempotency_records = {}

    @property
    def provider_name(self) -> str:
        return "ReliableMock"

    def initiate_call(
        self,
        phone_number: str,
        idempotency_key: str,
    ) -> ProviderCallResult:

        # Return the original result for repeated requests.
        if idempotency_key in self.idempotency_records:
            return self.idempotency_records[idempotency_key]

        start_time = time.perf_counter()

        self.total_calls += 1

        time.sleep(0.1)

        latency = (time.perf_counter() - start_time) * 1000
        self.latency_ms = latency

        result = ProviderCallResult(
            success=True,
            provider_name=self.provider_name,
            provider_call_id=f"REL-{uuid.uuid4().hex[:12]}",
        )

        # Persist the result in the mock provider's idempotency store.
        self.idempotency_records[idempotency_key] = result

        return result

    def find_call_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> ProviderCallResult | None:

        # Retrieve an existing provider call without initiating another.
        return self.idempotency_records.get(idempotency_key)

    def get_health(self) -> ProviderHealth:

        error_rate = (
            self.failed_calls / self.total_calls
            if self.total_calls > 0
            else 0.0
        )

        return ProviderHealth(
            provider_name=self.provider_name,
            is_healthy=error_rate < 0.05,
            latency_ms=self.latency_ms,
            error_rate=error_rate,
        )

    def normalize_event(self, payload: dict) -> dict:

        event_mapping = {
            "call_started": "INITIATED",
            "ringing": "RINGING",
            "answered": "ANSWERED",
            "completed": "COMPLETED",
            "failed": "FAILED",
        }

        event_type = payload.get("event_type")

        return {
            "provider_name": self.provider_name,
            "provider_event_id": payload.get(
                "event_id",
                str(uuid.uuid4()),
            ),
            "event_type": event_mapping.get(
                event_type,
                "UNKNOWN",
            ),
            "provider_call_id": payload.get("call_id"),
        }