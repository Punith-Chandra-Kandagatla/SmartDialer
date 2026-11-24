import time
import uuid

from app.providers.base import (
    BaseTelecomProvider,
    ProviderCallResult,
    ProviderHealth,
)


class UnreliableMockProvider(BaseTelecomProvider):

    def __init__(self):
        self.total_calls = 0
        self.failed_calls = 0
        self.timeout_calls = 0
        self.latency_ms = 350

        # Stores provider-side idempotency records.
        self.idempotency_records = {}

    @property
    def provider_name(self) -> str:
        return "UnreliableMock"

    def initiate_call(
        self,
        phone_number: str,
        idempotency_key: str,
    ) -> ProviderCallResult:

        # Prevent duplicate calls for the same key.
        if idempotency_key in self.idempotency_records:
            return self.idempotency_records[idempotency_key]

        self.total_calls += 1
        call_number = self.total_calls

        start_time = time.perf_counter()
        time.sleep(0.35)

        self.latency_ms = (
            time.perf_counter() - start_time
        ) * 1000

        if call_number % 7 == 0:
            self.timeout_calls += 1
            self.failed_calls += 1

            raise TimeoutError(
                "Telecom provider request timed out"
            )

        if call_number % 5 == 0:
            self.failed_calls += 1

            result = ProviderCallResult(
                success=False,
                provider_name=self.provider_name,
                error_message="Simulated provider failure",
            )

            self.idempotency_records[idempotency_key] = result

            return result

        result = ProviderCallResult(
            success=True,
            provider_name=self.provider_name,
            provider_call_id=f"UNR-{uuid.uuid4().hex[:12]}",
        )

        self.idempotency_records[idempotency_key] = result

        return result

    def find_call_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> ProviderCallResult | None:

        return self.idempotency_records.get(idempotency_key)

    def get_health(self) -> ProviderHealth:

        error_rate = (
            self.failed_calls / self.total_calls
            if self.total_calls > 0
            else 0.0
        )

        return ProviderHealth(
            provider_name=self.provider_name,
            is_healthy=(
                error_rate < 0.20
                and self.latency_ms < 1000
            ),
            latency_ms=self.latency_ms,
            error_rate=error_rate,
        )

    def normalize_event(self, payload: dict) -> dict:

        event_mapping = {
            "initiated": "INITIATED",
            "alerting": "RINGING",
            "connected": "ANSWERED",
            "ended": "COMPLETED",
            "error": "FAILED",
        }

        event_type = payload.get("status")

        return {
            "provider_name": self.provider_name,
            "provider_event_id": payload.get(
                "reference",
                str(uuid.uuid4()),
            ),
            "event_type": event_mapping.get(
                event_type,
                "UNKNOWN",
            ),
            "provider_call_id": payload.get("uuid"),
        }