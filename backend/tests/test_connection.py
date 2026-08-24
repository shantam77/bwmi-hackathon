from datetime import timedelta

from app import store
from app.domain import refund as refund_domain
from app.domain import tdr as tdr_domain
from app.engine import connection, state
from app.models import PassengerInput
from tests.conftest import requires_db

pytestmark = requires_db

# The exact flagship persona journey: 12295 SBC->NGP (arrives 06:15 +1day),
# 145-minute layover, 12539 NGP->BSB (departs 08:40 +1day).
LEG1 = dict(
    train_number="12295",
    train_name="Sanghamitra Express",
    from_station="SBC",
    to_station="NGP",
    departure="20:00",
    arrival="06:15",
    arrival_day_offset=1,
    travel_class="SL",
)
LEG2 = dict(
    train_number="12539",
    train_name="Nagpur Varanasi Express",
    from_station="NGP",
    to_station="BSB",
    departure="08:40",
    arrival="21:10",
    arrival_day_offset=1,
    travel_class="SL",
)


def _book_connecting_journey(session_id, leg1_status="AVAILABLE"):
    leg1_pnr = f"c1{session_id[-6:]}"
    leg2_pnr = f"c2{session_id[-6:]}"
    passengers = [PassengerInput(name="Shantam", age=27), PassengerInput(name="Ravi", age=61)]

    store.create_pnr(
        session_id=session_id,
        pnr_number=leg1_pnr,
        train_number=LEG1["train_number"],
        train_name=LEG1["train_name"],
        from_station=LEG1["from_station"],
        to_station=LEG1["to_station"],
        date="2026-09-04",
        departure=LEG1["departure"],
        arrival=LEG1["arrival"],
        arrival_day_offset=LEG1["arrival_day_offset"],
        travel_class=LEG1["travel_class"],
        status=leg1_status,
        fare_total=1240,
        passengers=passengers,
    )
    store.create_pnr(
        session_id=session_id,
        pnr_number=leg2_pnr,
        train_number=LEG2["train_number"],
        train_name=LEG2["train_name"],
        from_station=LEG2["from_station"],
        to_station=LEG2["to_station"],
        date="2026-09-05",  # leg 2 departs the day after leg 1's SBC departure
        departure=LEG2["departure"],
        arrival=LEG2["arrival"],
        arrival_day_offset=LEG2["arrival_day_offset"],
        travel_class=LEG2["travel_class"],
        status="AVAILABLE",
        fare_total=1890,
        passengers=passengers,
        linked_pnr=leg1_pnr,
    )
    leg1 = store.get_pnr(session_id, leg1_pnr)
    leg2 = store.get_pnr(session_id, leg2_pnr)
    return leg1, leg2


def test_linking_is_bidirectional(fake_session_id):
    leg1, leg2 = _book_connecting_journey(fake_session_id)
    assert leg2.linked_pnr == leg1.pnr
    assert leg1.linked_pnr == leg2.pnr


def test_flagship_delay_breaks_the_connection(fake_session_id):
    # 3h20m delay -> arrives NGP 09:35, leg2 departs 08:40 -- missed, matches
    # the PDD exactly.
    leg1, leg2 = _book_connecting_journey(fake_session_id)
    state.apply_demo_state(fake_session_id, leg1, "delay_3h")
    leg1_status = state.compute_status(fake_session_id, leg1)
    assert connection.connection_is_broken(leg1, leg1_status, leg2) is True


def test_small_delay_does_not_break_the_connection(fake_session_id):
    leg1, leg2 = _book_connecting_journey(fake_session_id)
    state.apply_demo_state(fake_session_id, leg1, "delay_1h")
    leg1_status = state.compute_status(fake_session_id, leg1)
    assert connection.connection_is_broken(leg1, leg1_status, leg2) is False


def test_connection_with_exactly_the_minimum_buffer_is_not_broken(fake_session_id):
    # Boundary edge case from the Phase 4 test gate: a tight but still
    # technically makeable connection must NOT trigger Flow H. Layover is
    # 145 minutes; a 130-minute delay leaves exactly 15 (the minimum).
    leg1, leg2 = _book_connecting_journey(fake_session_id)
    from app.engine import clock

    departure = state.scheduled_departure(leg1)
    clock.jump_to(fake_session_id, departure + timedelta(minutes=130))
    leg1_status = state.compute_status(fake_session_id, leg1)
    assert leg1_status.delay_minutes == 130
    assert connection.connection_is_broken(leg1, leg1_status, leg2) is False


def test_connection_one_minute_past_the_minimum_buffer_is_broken(fake_session_id):
    leg1, leg2 = _book_connecting_journey(fake_session_id)
    from app.engine import clock

    departure = state.scheduled_departure(leg1)
    clock.jump_to(fake_session_id, departure + timedelta(minutes=131))
    leg1_status = state.compute_status(fake_session_id, leg1)
    assert connection.connection_is_broken(leg1, leg1_status, leg2) is True


def test_cancelled_leg1_always_breaks_the_connection(fake_session_id):
    leg1, leg2 = _book_connecting_journey(fake_session_id)
    state.apply_demo_state(fake_session_id, leg1, "cancelled")
    leg1_status = state.compute_status(fake_session_id, leg1)
    assert connection.connection_is_broken(leg1, leg1_status, leg2) is True


def test_rebooking_finds_the_1420_train_with_6_seats(fake_session_id):
    # Matches PDD Flow H exactly: "There's a 14:20 Nagpur-Varanasi, 6
    # sleeper seats, same ₹1,890."
    leg1, leg2 = _book_connecting_journey(fake_session_id)
    state.apply_demo_state(fake_session_id, leg1, "delay_3h")
    leg1_status = state.compute_status(fake_session_id, leg1)
    rebooking = connection.find_rebooking_option(leg1, leg1_status, leg2)
    assert rebooking is not None
    assert rebooking.train_number == "15665"
    assert rebooking.departure == "14:20"
    assert rebooking.seats_or_position == 6
    assert rebooking.fare_per_passenger == 945


def test_decision_block_option_1_figures_trace_to_domain_functions_directly(fake_session_id):
    leg1, leg2 = _book_connecting_journey(fake_session_id)
    state.apply_demo_state(fake_session_id, leg1, "delay_3h")
    leg1_status = state.compute_status(fake_session_id, leg1)
    block = connection.build_decision_block(leg1, leg1_status, leg2)

    # Independently recompute leg1's refund via domain/tdr.py + domain/refund.py.
    leg1_eligibility = tdr_domain.check_delay_eligibility(
        timedelta(minutes=leg1_status.delay_minutes), state.scheduled_departure(leg1)
    )
    expected_leg1_refund = refund_domain.tdr_refund(leg1.total_fare, leg1_eligibility.refund_basis)

    # Independently recompute leg2's ordinary cancellation refund.
    from datetime import datetime

    now = datetime.fromisoformat(leg1_status.now_iso)
    expected_leg2_refund = refund_domain.ordinary_cancellation_refund(
        leg2.total_fare, leg2.travel_class, len(leg2.passengers), now, state.scheduled_departure(leg2)
    )

    leg1_item = next(i for i in block.option_1.items if "Leg 1" in i["label"])
    leg2_item = next(i for i in block.option_1.items if "Leg 2" in i["label"])
    assert leg1_item["amount"] == expected_leg1_refund.refund_amount
    assert leg2_item["amount"] == expected_leg2_refund.refund_amount
    assert block.option_1.bottom_line_recovered == (
        expected_leg1_refund.refund_amount + expected_leg2_refund.refund_amount
    )
    assert block.option_1.bottom_line_total_paid == leg1.total_fare + leg2.total_fare


def test_decision_block_option_2_uses_the_real_rebooking_fare(fake_session_id):
    leg1, leg2 = _book_connecting_journey(fake_session_id)
    state.apply_demo_state(fake_session_id, leg1, "delay_3h")
    leg1_status = state.compute_status(fake_session_id, leg1)
    block = connection.build_decision_block(leg1, leg1_status, leg2)

    rebooking_item = next(i for i in block.option_2.items if "Rebook" in i["label"])
    assert rebooking_item["amount"] == -945 * 2  # 15665's fare x 2 passengers


def test_leg2_rule_explanation_is_present_and_substantive(fake_session_id):
    leg1, leg2 = _book_connecting_journey(fake_session_id)
    state.apply_demo_state(fake_session_id, leg1, "delay_3h")
    leg1_status = state.compute_status(fake_session_id, leg1)
    block = connection.build_decision_block(leg1, leg1_status, leg2)
    assert "no concept of a connected journey" in block.leg2_rule_explanation
    assert len(block.leg2_rule_explanation) > 100
