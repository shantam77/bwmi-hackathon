import re

from app.domain.booking import generate_pnr, quote
from app.models import PassengerInput


def _quote(passengers, fare_per_passenger=620, seats_or_position=18, status="WL"):
    return quote(
        train_number="12295",
        train_name="Sanghamitra Express",
        from_station="SBC",
        to_station="NGP",
        date="2026-09-04",
        travel_class="SL",
        status=status,
        seats_or_position=seats_or_position,
        fare_per_passenger=fare_per_passenger,
        passengers=passengers,
    )


def test_total_fare_is_fare_per_passenger_times_count():
    passengers = [PassengerInput(name="Shantam", age=27), PassengerInput(name="Ravi", age=61)]
    result = _quote(passengers)
    assert result.total_fare == 620 * 2
    assert result.fare_per_passenger == 620


def test_matches_the_pdd_flow_c_figure_exactly():
    # docs/03-product-design-document.md Flow C: "Two sleeper berths, ₹1,240 total."
    passengers = [PassengerInput(name="Shantam", age=27), PassengerInput(name="Ravi", age=61)]
    result = _quote(passengers)
    assert result.total_fare == 1240


def test_senior_citizen_gets_lower_berth_applied_automatically():
    passengers = [PassengerInput(name="Ravi", age=61)]
    result = _quote(passengers)
    assert result.passengers[0].berth_preference == "lower"


def test_senior_citizen_note_names_the_passenger():
    passengers = [PassengerInput(name="Shantam", age=27), PassengerInput(name="Ravi", age=61)]
    result = _quote(passengers)
    assert result.senior_citizen_note is not None
    assert "Ravi" in result.senior_citizen_note
    assert "Shantam" not in result.senior_citizen_note


def test_no_senior_citizen_note_when_everyone_is_under_60():
    passengers = [PassengerInput(name="Shantam", age=27)]
    result = _quote(passengers)
    assert result.senior_citizen_note is None


def test_exactly_60_counts_as_senior():
    passengers = [PassengerInput(name="Border", age=60)]
    result = _quote(passengers)
    assert result.passengers[0].berth_preference == "lower"
    assert result.senior_citizen_note is not None


def test_explicit_berth_preference_is_not_overridden():
    passengers = [PassengerInput(name="Ravi", age=61, berth_preference="upper")]
    result = _quote(passengers)
    assert result.passengers[0].berth_preference == "upper"


def test_multiple_seniors_are_both_named():
    passengers = [PassengerInput(name="Ravi", age=61), PassengerInput(name="Geeta", age=65)]
    result = _quote(passengers)
    assert "Ravi" in result.senior_citizen_note
    assert "Geeta" in result.senior_citizen_note


def test_generated_pnr_is_ten_digits():
    pnr = generate_pnr()
    assert re.fullmatch(r"\d{10}", pnr)


def test_generated_pnrs_are_not_all_identical():
    pnrs = {generate_pnr() for _ in range(20)}
    assert len(pnrs) > 1
