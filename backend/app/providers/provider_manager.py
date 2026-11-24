from app.providers.base import BaseTelecomProvider


class ProviderManager:

    def __init__(self):

        self.providers: dict[str, BaseTelecomProvider] = {}

    def register_provider(
        self,
        provider: BaseTelecomProvider,
    ) -> None:

        name = provider.provider_name

        if name in self.providers:
            raise ValueError(
                f"Provider already registered: {name}"
            )

        self.providers[name] = provider

    def get_provider(
        self,
        provider_name: str,
    ) -> BaseTelecomProvider:

        provider = self.providers.get(provider_name)

        if provider is None:
            raise ValueError(
                f"Unknown provider: {provider_name}"
            )

        return provider

    def get_provider_health(self) -> list[dict]:

        health_reports = []

        for provider in self.providers.values():

            health = provider.get_health()

            health_reports.append({
                "provider_name": health.provider_name,
                "is_healthy": health.is_healthy,
                "latency_ms": round(health.latency_ms, 2),
                "error_rate": round(health.error_rate, 4),
            })

        return health_reports

    def select_healthy_provider(
        self,
    ) -> BaseTelecomProvider | None:

        healthy_providers = []

        for provider in self.providers.values():

            health = provider.get_health()

            if health.is_healthy:

                healthy_providers.append(
                    (provider, health)
                )

        if not healthy_providers:
            return None

        # Prefer lower latency and lower error rate
        healthy_providers.sort(
            key=lambda item: (
                item[1].latency_ms,
                item[1].error_rate,
            )
        )

        return healthy_providers[0][0]