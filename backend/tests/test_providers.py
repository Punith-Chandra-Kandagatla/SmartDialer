import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.providers.reliable_provider import ReliableMockProvider
from app.providers.unreliable_provider import UnreliableMockProvider


def test_reliable_provider():

    provider = ReliableMockProvider()

    result = provider.initiate_call(
        phone_number="+919999999999",
        idempotency_key="TEST-REL-001",
    )

    assert result.success is True
    assert result.provider_name == "ReliableMock"
    assert result.provider_call_id is not None

    health = provider.get_health()

    assert health.is_healthy is True

    event = provider.normalize_event({
        "event_id": "EVT-001",
        "event_type": "answered",
        "call_id": "CALL-001",
    })

    assert event["event_type"] == "ANSWERED"

    print("Reliable provider test: PASSED")


def test_unreliable_provider():

    provider = UnreliableMockProvider()

    # Calls 1–4 should succeed
    for i in range(4):

        result = provider.initiate_call(
            phone_number="+919999999999",
            idempotency_key=f"TEST-UNR-{i + 1}",
        )

        assert result.success is True

    # Fifth call should fail
    result = provider.initiate_call(
        phone_number="+919999999999",
        idempotency_key="TEST-UNR-005",
    )

    assert result.success is False

    # Sixth call should succeed
    result = provider.initiate_call(
        phone_number="+919999999999",
        idempotency_key="TEST-UNR-006",
    )

    assert result.success is True

    # Seventh call should timeout
    try:
        provider.initiate_call(
            phone_number="+919999999999",
            idempotency_key="TEST-UNR-007",
        )

        assert False, "Expected TimeoutError"

    except TimeoutError:
        print("Provider timeout simulation: PASSED")

    assert provider.total_calls == 7
    assert provider.failed_calls == 2
    assert provider.timeout_calls == 1

    health = provider.get_health()

    assert health.error_rate > 0
    assert health.is_healthy is False

    event = provider.normalize_event({
        "reference": "EVT-002",
        "status": "alerting",
        "uuid": "CALL-002",
    })

    assert event["event_type"] == "RINGING"

    print("Unreliable provider failure simulation: PASSED")
    print("Provider health monitoring: PASSED")


if __name__ == "__main__":

    test_reliable_provider()
    test_unreliable_provider()

    print("\nALL PROVIDER TESTS PASSED!")
    