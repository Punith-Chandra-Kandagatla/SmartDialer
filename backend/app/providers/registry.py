from app.providers.provider_manager import ProviderManager
from app.providers.reliable_provider import ReliableMockProvider
from app.providers.unreliable_provider import UnreliableMockProvider


provider_manager = ProviderManager()

provider_manager.register_provider(
    ReliableMockProvider()
)

provider_manager.register_provider(
    UnreliableMockProvider()
)