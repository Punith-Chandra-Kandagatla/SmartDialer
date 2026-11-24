import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.providers.reliable_provider import ReliableMockProvider
def test_provider_idempotency():

    provider = ReliableMockProvider()

    # First request
    first_result = provider.initiate_call(
        phone_number="+919888000001",
        idempotency_key="CALL-123",
    )

    # Retry using the same key
    retry_result = provider.initiate_call(
        phone_number="+919888000001",
        idempotency_key="CALL-123",
    )

    assert first_result.success is True
    assert retry_result.success is True

    # Both requests must return the same provider call ID
    assert (
        first_result.provider_call_id
        == retry_result.provider_call_id
    )

    # Provider must have initiated only one call
    assert provider.total_calls == 1

    print("First provider call:", first_result.provider_call_id)
    print("Retry provider call:", retry_result.provider_call_id)
    print("Actual outbound calls:", provider.total_calls)

    print("\nPROVIDER IDEMPOTENCY TEST PASSED!")


if __name__ == "__main__":
    test_provider_idempotency()