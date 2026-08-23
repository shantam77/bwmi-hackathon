"""Passenger validation, fare totals, and PNR generation. Pure Python -- no
FastAPI, no OpenAI, no ORM imports."""

import random

from app.models import BookingQuote, PassengerInput

SENIOR_CITIZEN_AGE = 60


def quote(
    train_number: str,
    train_name: str,
    from_station: str,
    to_station: str,
    date: str,
    travel_class: str,
    status: str,
    seats_or_position: int,
    fare_per_passenger: int,
    passengers: list[PassengerInput],
) -> BookingQuote:
    passengers = _apply_senior_citizen_preference(passengers)
    total_fare = fare_per_passenger * len(passengers)

    return BookingQuote(
        train_number=train_number,
        train_name=train_name,
        from_station=from_station,
        to_station=to_station,
        date=date,
        travel_class=travel_class,
        status=status,
        seats_or_position=seats_or_position,
        passengers=passengers,
        fare_per_passenger=fare_per_passenger,
        total_fare=total_fare,
        senior_citizen_note=_senior_citizen_note(passengers),
    )


def _apply_senior_citizen_preference(passengers: list[PassengerInput]) -> list[PassengerInput]:
    updated = []
    for p in passengers:
        if p.age >= SENIOR_CITIZEN_AGE and p.berth_preference is None:
            p = p.model_copy(update={"berth_preference": "lower"})
        updated.append(p)
    return updated


def _senior_citizen_note(passengers: list[PassengerInput]) -> str | None:
    seniors = [p for p in passengers if p.age >= SENIOR_CITIZEN_AGE]
    if not seniors:
        return None
    names = " and ".join(p.name for p in seniors)
    verb = "qualify" if len(seniors) > 1 else "qualifies"
    return (
        f"{names} {verb} for the senior citizen lower-berth preference, "
        "which improves the allocation odds. I've applied it."
    )


def generate_pnr() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(10))
