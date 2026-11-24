from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ProviderCallResult:
    success: bool
    provider_name: str
    provider_call_id: str | None = None
    error_message: str | None = None


@dataclass
class ProviderHealth:
    provider_name: str
    is_healthy: bool
    latency_ms: float
    error_rate: float


class BaseTelecomProvider(ABC):

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    def initiate_call(
        self,
        phone_number: str,
        idempotency_key: str,
    ) -> ProviderCallResult:
        pass

    @abstractmethod
    def find_call_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> ProviderCallResult | None:
        """
        Look up an existing provider call using its idempotency key.

        Returns:
            ProviderCallResult: Matching call found.
            None: No matching call found.

        Raises:
            Exception: Provider lookup could not be completed.
        """
        pass

    @abstractmethod
    def get_health(self) -> ProviderHealth:
        pass

    @abstractmethod
    def normalize_event(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        pass