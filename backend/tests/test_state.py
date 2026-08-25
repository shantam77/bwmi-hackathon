from datetime import datetime, timedelta, timezone

from app import store
from app.engine import clock, state
from app.models import PassengerInput
from tests.conftest import requires_db

pytestmark = requires_db

# Each of these round-trips to Postgres over the public proxy at least twice
# (write the offset, then read it back via clock.now()), which can add a
# couple of real seconds of latency -- see tests/test_clock.py for the same
# lesson. Check the target time was hit closely, not to the microsecond.
TOLERANCE_SECONDS = 8


def _assert_close(iso_string: str, expected: datetime) -> None:
    actual = datetime.fromisoformat(iso_string)
    assert abs((actual - expected).total_seconds()) < TOLERANCE_SECONDS

# 12295 SL GNWL/18 -> 55% probable -> clears (>= 50% threshold).
CLEARS_TRAIN = dict(
    train_number="12295",
    train_name="Sanghamitra Express",
    from_station="SBC",
    to_station="NGP",
    departure="20:00",
    arrival="06:15",
    arrival_day_offset=1,
    travel_class="SL",
)
# 22823 SL GNWL/45 -> 0% -> does not clear.
DOES_NOT_CLEAR_TRAIN = dict(
    train_number="22823",
    train_name="Bengaluru Nagpur SF Express",
    from_station="YPR",
    to_station="NGP",
    departure="09:30",
    arrival="19:20",
    arrival_day_offset=0,
    travel_class="SL",
)
# 12539 NGP -> BSB, confirmed -- the real flagship's leg 2, departing the
# NEXT calendar day after leg 1's evening departure. Used specifically
# where a test needs leg 2 to still be in the future relative to leg 1's
# demo-adjusted "now" (unlike DOES_NOT_CLEAR_TRAIN's same-day 09:30, which
# a delay_3h-shifted "now" of ~22:33 has already passed).
LEG2_TRAIN = dict(
    train_number="12539",
    train_name="Nagpur Varanasi Express",
    from_station="NGP",
    to_station="BSB",
    departure="08:40",
    arrival="21:10",
    arrival_day_offset=0,
    travel_class="SL",
)


def _book(session_id, train, status, date="2026-09-04", pnr_suffix=""):
    pnr_number = f"test{session_id[-6:]}{pnr_suffix}"
    store.create_pnr(
        session_id=session_id,
        pnr_number=pnr_number,
        train_number=train["train_number"],
        train_name=train["train_name"],
        from_station=train["from_station"],
        to_station=train["to_station"],
        date=date,
        departure=train["departure"],
        arrival=train["arrival"],
        arrival_day_offset=train["arrival_day_offset"],
        travel_class=train["travel_class"],
        status=status,
        fare_total=1000,
        passengers=[PassengerInput(name="Test", age=30)],
    )
    return store.get_pnr(session_id, pnr_number)


def test_chart_prepared_sets_clock_four_hours_before_departure(fake_session_id):
    pnr = _book(fake_session_id, CLEARS_TRAIN, "WL")
    state.apply_demo_state(fake_session_id, pnr, "chart_prepared")
    status = state.compute_status(fake_session_id, pnr)
    departure = state.scheduled_departure(pnr)
    expected = departure - timedelta(hours=4)
    _assert_close(status.now_iso, expected)
    assert status.chart_prepared is True


def test_boarding_day_sets_clock_one_hour_before_departure(fake_session_id):
    pnr = _book(fake_session_id, CLEARS_TRAIN, "WL")
    state.apply_demo_state(fake_session_id, pnr, "boarding_day")
    status = state.compute_status(fake_session_id, pnr)
    departure = state.scheduled_departure(pnr)
    _assert_close(status.now_iso, departure - timedelta(hours=1))


def test_delay_1h_matches_pdd_wording_of_1h5m_late(fake_session_id):
    pnr = _book(fake_session_id, CLEARS_TRAIN, "WL")
    state.apply_demo_state(fake_session_id, pnr, "delay_1h")
    status = state.compute_status(fake_session_id, pnr)
    assert status.delay_minutes == 65


def test_delay_3h_matches_pdd_flagship_figures_exactly(fake_session_id):
    pnr = _book(fake_session_id, CLEARS_TRAIN, "WL")
    state.apply_demo_state(fake_session_id, pnr, "delay_3h")
    status = state.compute_status(fake_session_id, pnr)
    departure = state.scheduled_departure(pnr)
    actual_departure = departure + timedelta(minutes=200)

    assert status.delay_minutes == 200  # "running 3h 20m late"
    assert status.tdr_eligible is True
    assert status.tdr_deadline_iso == actual_departure.isoformat()

    # "That's 47 minutes from now." -- checked against the real computed
    # `now`, not assumed, so this actually verifies the countdown a
    # CountdownChip would show, not just the deadline arithmetic above.
    now = datetime.fromisoformat(status.now_iso)
    deadline = datetime.fromisoformat(status.tdr_deadline_iso)
    minutes_to_deadline = (deadline - now).total_seconds() / 60
    assert abs(minutes_to_deadline - 47) < 1


def test_delay_at_2h59m_is_not_tdr_eligible(fake_session_id):
    # Explicit boundary edge case from the Phase 3 test gate.
    pnr = _book(fake_session_id, CLEARS_TRAIN, "AVAILABLE")
    departure = state.scheduled_departure(pnr)
    clock.jump_to(fake_session_id, departure + timedelta(minutes=179))
    status = state.compute_status(fake_session_id, pnr)
    assert status.delay_minutes == 179
    assert status.tdr_eligible is False


def test_delay_at_exactly_3h_is_tdr_eligible(fake_session_id):
    pnr = _book(fake_session_id, CLEARS_TRAIN, "AVAILABLE")
    departure = state.scheduled_departure(pnr)
    clock.jump_to(fake_session_id, departure + timedelta(minutes=180))
    status = state.compute_status(fake_session_id, pnr)
    assert status.delay_minutes == 180
    assert status.tdr_eligible is True


def test_cancelled_is_auto_refund_not_tdr_eligible(fake_session_id):
    pnr = _book(fake_session_id, CLEARS_TRAIN, "AVAILABLE")
    state.apply_demo_state(fake_session_id, pnr, "cancelled")
    status = state.compute_status(fake_session_id, pnr)
    assert status.is_cancelled is True
    assert status.tdr_auto_refund is True
    assert status.tdr_eligible is False
    assert status.retiring_room_eligible is False


def test_wl_that_clears_becomes_confirmed_at_chart_prep(fake_session_id):
    pnr = _book(fake_session_id, CLEARS_TRAIN, "WL")
    state.apply_demo_state(fake_session_id, pnr, "chart_prepared")
    status = state.compute_status(fake_session_id, pnr)
    assert status.cleared is True
    assert status.effective_status == "CNF"
    assert status.tdr_auto_refund is False
    assert status.retiring_room_eligible is True


def test_wl_that_does_not_clear_is_auto_refund(fake_session_id):
    pnr = _book(fake_session_id, DOES_NOT_CLEAR_TRAIN, "WL")
    state.apply_demo_state(fake_session_id, pnr, "chart_prepared")
    status = state.compute_status(fake_session_id, pnr)
    assert status.cleared is False
    assert status.effective_status == "WL"
    assert status.tdr_auto_refund is True
    assert status.tdr_eligible is False
    assert status.retiring_room_eligible is False


def test_wl_before_chart_prep_is_not_yet_resolved(fake_session_id):
    pnr = _book(fake_session_id, CLEARS_TRAIN, "WL")
    # No demo state applied -- clock is at real time, long before 2026-09-04.
    status = state.compute_status(fake_session_id, pnr)
    assert status.chart_prepared is False
    assert status.cleared is None
    assert status.effective_status == "WL"
    assert status.retiring_room_eligible is False


def test_confirmed_pnr_is_retiring_room_eligible_immediately(fake_session_id):
    pnr = _book(fake_session_id, CLEARS_TRAIN, "AVAILABLE")
    status = state.compute_status(fake_session_id, pnr)
    assert status.effective_status == "CNF"
    assert status.retiring_room_eligible is True


def test_rac_status_maps_to_rac_and_is_retiring_room_eligible(fake_session_id):
    pnr = _book(fake_session_id, CLEARS_TRAIN, "RAC")
    status = state.compute_status(fake_session_id, pnr)
    assert status.effective_status == "RAC"
    assert status.retiring_room_eligible is True


def test_demo_delay_does_not_leak_onto_a_different_pnr_in_the_same_session(fake_session_id):
    # Regression test for a real bug found via live E2E testing Flow H:
    # applying "delay_3h" to the primary PNR (leg 1) must NOT make a
    # DIFFERENT PNR booked in the same session (leg 2) also report as
    # delayed -- leg 2's own train was never actually late. Found because
    # choosing "Abandon both" filed leg 2's TDR as a 3-hour-delay claim for
    # the full fare instead of an ordinary cancellation at 50%.
    leg1 = _book(fake_session_id, CLEARS_TRAIN, "WL", pnr_suffix="a")
    leg2 = _book(fake_session_id, LEG2_TRAIN, "AVAILABLE", date="2026-09-05", pnr_suffix="b")

    state.apply_demo_state(fake_session_id, leg1, "delay_3h")

    leg1_status = state.compute_status(fake_session_id, leg1)
    leg2_status = state.compute_status(fake_session_id, leg2)

    assert leg1_status.delay_minutes == 200
    assert leg1_status.tdr_eligible is True

    # leg2 departs the next morning -- still in the future relative to
    # leg1's demo-shifted "now" (~22:33 the evening before), so this
    # correctly isolates the leak (0 = fixed) from the unrelated, correct
    # "already departed" fallback (which a same-day-earlier leg2 would hit
    # regardless of the leak).
    assert leg2_status.delay_minutes == 0
    assert leg2_status.tdr_eligible is False


def test_demo_cancellation_does_not_leak_onto_a_different_pnr_in_the_same_session(fake_session_id):
    leg1 = _book(fake_session_id, CLEARS_TRAIN, "WL", pnr_suffix="a")
    leg2 = _book(fake_session_id, DOES_NOT_CLEAR_TRAIN, "AVAILABLE", pnr_suffix="b")

    state.apply_demo_state(fake_session_id, leg1, "cancelled")

    leg1_status = state.compute_status(fake_session_id, leg1)
    leg2_status = state.compute_status(fake_session_id, leg2)

    assert leg1_status.is_cancelled is True
    assert leg1_status.tdr_auto_refund is True

    assert leg2_status.is_cancelled is False
    assert leg2_status.tdr_auto_refund is False


def test_reset_clears_demo_state_and_offset(fake_session_id):
    pnr = _book(fake_session_id, CLEARS_TRAIN, "WL")
    state.apply_demo_state(fake_session_id, pnr, "delay_3h")
    assert store.get_demo_state(fake_session_id) == "delay_3h"

    state.apply_demo_state(fake_session_id, pnr, "reset")
    assert store.get_demo_state(fake_session_id) is None
    assert store.get_clock_offset_seconds(fake_session_id) == 0
