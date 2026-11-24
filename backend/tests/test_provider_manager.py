import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from app.providers.provider_manager import ProviderManager
from app.providers.reliable_provider import ReliableMockProvider
from app.providers.unreliable_provider import UnreliableMockProvider


def test_provider_registration():

    manager = ProviderManager()

    reliable = ReliableMockProvider()
    unreliable = UnreliableMockProvider()

    manager.register_provider(reliable)
    manager.register_provider(unreliable)

    assert len(manager.providers) == 2

    print("Provider registration: PASSED")


def test_provider_retrieval():

    manager = ProviderManager()

    reliable = ReliableMockProvider()
    manager.register_provider(reliable)

    retrieved = manager.get_provider("ReliableMock")

    assert retrieved is reliable

    print("Provider retrieval: PASSED")


def test_duplicate_registration():

    manager = ProviderManager()

    manager.register_provider(ReliableMockProvider())

    with pytest.raises(ValueError):
        manager.register_provider(ReliableMockProvider())

    print("Duplicate registration protection: PASSED")


def test_unknown_provider():

    manager = ProviderManager()

    with pytest.raises(ValueError):
        manager.get_provider("UnknownProvider")

    print("Unknown provider protection: PASSED")


def test_provider_health():

    manager = ProviderManager()

    manager.register_provider(ReliableMockProvider())
    manager.register_provider(UnreliableMockProvider())

    reports = manager.get_provider_health()

    assert len(reports) == 2

    assert all(
        "provider_name" in report
        and "is_healthy" in report
        and "latency_ms" in report
        and "error_rate" in report
        for report in reports
    )

    print("Provider health monitoring: PASSED")


def test_healthy_provider_selection():

    manager = ProviderManager()

    reliable = ReliableMockProvider()
    unreliable = UnreliableMockProvider()

    manager.register_provider(reliable)
    manager.register_provider(unreliable)

    selected = manager.select_healthy_provider()

    # Reliable provider has lower initial latency
    assert selected is reliable

    print("Healthy provider selection: PASSED")


def test_no_healthy_provider():

    manager = ProviderManager()

    selected = manager.select_healthy_provider()

    assert selected is None

    print("No healthy provider handling: PASSED")


if __name__ == "__main__":

    test_provider_registration()
    test_provider_retrieval()
    test_duplicate_registration()
    test_unknown_provider()
    test_provider_health()
    test_healthy_provider_selection()
    test_no_healthy_provider()

    print("\nALL PROVIDER MANAGER TESTS PASSED!")