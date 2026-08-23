from app import store
from app.engine import alerts, state
from app.models import PassengerInput
from tests.conftest import requires_db

pytestmark = requires_db

CLEARS_TRAIN = dict(
    train_number="12295",
    train_name="Sanghamitra Express",
    from_station="SBC",
    to_station="NGP",
    departure="20:00",
    travel_class="SL",
)
DOES_NOT_CLEAR_TRAIN = dict(
    train_number="22823",
    train_name="Bengaluru Nagpur SF Express",
    from_station="YPR",
    to_station="NGP",
    departure="09:30",
    travel_class="SL",
)


def _book(session_id, train, status, date="2026-09-04"):
    pnr_number = f"al{session_id[-6:]}"
    store.create_pnr(
        session_id=session_id,
        pnr_number=pnr_number,
        train_number=train["train_number"],
        train_name=train["train_name"],
        from_station=train["from_station"],
        to_station=train["to_station"],
        date=date,
        departure=train["departure"],
        travel_class=train["travel_class"],
        status=status,
        fare_total=1240,
        passengers=[PassengerInput(name="Shantam", age=27), PassengerInput(name="Ravi", age=61)],
    )
    return store.get_pnr(session_id, pnr_number)


def _advance(session_id, pnr, demo_state):
    state.apply_demo_state(session_id, pnr, demo_state)
    status = state.compute_status(session_id, pnr)
    return status, alerts.evaluate(session_id, pnr, status)


def test_chart_prepared_fires_d2_for_a_wl_ticket_that_clears(fake_session_id):
    pnr = _book(fake_session_id, CLEARS_TRAIN, "WL")
    _, fired = _advance(fake_session_id, pnr, "chart_prepared")
    ids = [a.alert_id for a in fired]
    assert "D2" in ids
    assert "D3" not in ids


def test_chart_prepared_fires_d3_for_a_wl_ticket_that_does_not_clear(fake_session_id):
    pnr = _book(fake_session_id, DOES_NOT_CLEAR_TRAIN, "WL")
    _, fired = _advance(fake_session_id, pnr, "chart_prepared")
    ids = [a.alert_id for a in fired]
    assert "D3" in ids
    assert "D2" not in ids
    d3 = next(a for a in fired if a.alert_id == "D3")
    assert d3.severity == "critical"
    assert "1,240" in d3.message or "1240" in d3.message


def test_chart_prepared_never_fires_both_d2_and_d3(fake_session_id):
    pnr = _book(fake_session_id, CLEARS_TRAIN, "WL")
    _, fired = _advance(fake_session_id, pnr, "chart_prepared")
    ids = [a.alert_id for a in fired]
    assert not ({"D2", "D3"} <= set(ids))


def test_no_chart_alert_for_an_already_confirmed_ticket(fake_session_id):
    pnr = _book(fake_session_id, CLEARS_TRAIN, "AVAILABLE")
    _, fired = _advance(fake_session_id, pnr, "chart_prepared")
    ids = [a.alert_id for a in fired]
    assert "D2" not in ids and "D3" not in ids


def test_delay_below_1h_does_not_fire_d6(fake_session_id):
    pnr = _book(fake_session_id, CLEARS_TRAIN, "AVAILABLE")
    from datetime import timedelta

    from app.engine import clock

    departure = state._scheduled_departure(pnr)
    clock.jump_to(fake_session_id, departure + timedelta(minutes=45))
    status = state.compute_status(fake_session_id, pnr)
    fired = alerts.evaluate(fake_session_id, pnr, status)
    assert "D6" not in [a.alert_id for a in fired]


def test_delay_1h_fires_d6_not_d8(fake_session_id):
    pnr = _book(fake_session_id, CLEARS_TRAIN, "AVAILABLE")
    _, fired = _advance(fake_session_id, pnr, "delay_1h")
    ids = [a.alert_id for a in fired]
    assert "D6" in ids
    assert "D8" not in ids


def test_delay_3h_fires_d8_critical_and_requires_reasoning(fake_session_id):
    pnr = _book(fake_session_id, CLEARS_TRAIN, "AVAILABLE")
    _, fired = _advance(fake_session_id, pnr, "delay_3h")
    d8 = next(a for a in fired if a.alert_id == "D8")
    assert d8.severity == "critical"
    assert d8.requires_reasoning is True
    assert d8.payload["delay_minutes"] == 200
    assert d8.payload["tdr_deadline_iso"] is not None


def test_cancelled_does_not_fire_d8(fake_session_id):
    pnr = _book(fake_session_id, CLEARS_TRAIN, "AVAILABLE")
    _, fired = _advance(fake_session_id, pnr, "cancelled")
    assert "D8" not in [a.alert_id for a in fired]


def test_d9_fires_when_a_wl_ticket_clears_into_a_retiring_room_eligible_state(fake_session_id):
    pnr = _book(fake_session_id, CLEARS_TRAIN, "WL")
    _, fired = _advance(fake_session_id, pnr, "chart_prepared")
    ids = [a.alert_id for a in fired]
    assert "D9" in ids


def test_d9_does_not_fire_for_a_wl_ticket_that_does_not_clear(fake_session_id):
    pnr = _book(fake_session_id, DOES_NOT_CLEAR_TRAIN, "WL")
    _, fired = _advance(fake_session_id, pnr, "chart_prepared")
    assert "D9" not in [a.alert_id for a in fired]


def test_reaching_the_same_demo_state_twice_does_not_refire(fake_session_id):
    pnr = _book(fake_session_id, CLEARS_TRAIN, "WL")
    _, first = _advance(fake_session_id, pnr, "chart_prepared")
    assert len(first) > 0

    _, second = _advance(fake_session_id, pnr, "chart_prepared")
    assert second == []


def test_advancing_to_a_worse_demo_state_fires_new_alerts(fake_session_id):
    pnr = _book(fake_session_id, CLEARS_TRAIN, "AVAILABLE")
    _, first = _advance(fake_session_id, pnr, "delay_1h")
    assert "D6" in [a.alert_id for a in first]

    _, second = _advance(fake_session_id, pnr, "delay_3h")
    assert "D8" in [a.alert_id for a in second]
    # D6 shouldn't refire either -- its dedup key is the specific delay
    # value, and delay_3h is a different (200-minute) value than delay_1h's
    # 65 minutes, so D6 doesn't apply at delay_3h's magnitude at all (it's
    # past the 180-minute D6 upper bound), which the not-in check confirms.
    assert "D6" not in [a.alert_id for a in second]


def test_evaluate_can_return_more_than_one_alert_in_one_batch(fake_session_id):
    # chart_prepared on a clearing WL ticket should fire D2 AND D9 together
    # -- proving multiple triggers can legitimately batch in a single
    # delivery, which is different from firing repeatedly over time.
    pnr = _book(fake_session_id, CLEARS_TRAIN, "WL")
    _, fired = _advance(fake_session_id, pnr, "chart_prepared")
    assert len(fired) >= 2
    assert {"D2", "D9"} <= {a.alert_id for a in fired}
