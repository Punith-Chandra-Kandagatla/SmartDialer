import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database.connection import SessionLocal
from app.models.call import Call
from app.services.reservation_service import ReservationService


CALL_IDS = [
    "12637704-0370-4980-9117-556c3cc13db5",
    "5f9d2e35-e910-4146-a807-e1ca8c4bf900",
]


with SessionLocal() as db:

    for call_id in CALL_IDS:

        call = db.get(Call, call_id)

        if call is None:
            print("Call not found:", call_id)
            continue

        released = ReservationService.release_reservation(
            db=db,
            call_id=call.id,
            reservation_token=call.reservation_token,
            failure_reason="Cleanup after concurrency test",
        )

        print("Call:", call_id, "| Released:", released)

    db.commit()

print("\nCleanup completed.")