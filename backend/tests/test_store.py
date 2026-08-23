from app import store
from app.models import JourneyPlan, Leg
from tests.conftest import requires_db

pytestmark = requires_db


def _sample_plan() -> JourneyPlan:
    leg = Leg(
        train_number="12295",
        train_name="Sanghamitra Express",
        from_station="SBC",
        to_station="NGP",
        departure="20:00",
        arrival="06:15",
        departure_day_offset=0,
        arrival_day_offset=1,
        travel_class="SL",
        status="WL",
        seats_or_position=18,
        fare_per_passenger=620,
    )
    return JourneyPlan(legs=[leg], direct=True)


def test_clock_offset_defaults_to_zero_for_an_unseen_session(fake_session_id):
    assert store.get_clock_offset_seconds(fake_session_id) == 0


def test_clock_offset_round_trips(fake_session_id):
    store.set_clock_offset_seconds(fake_session_id, 3600)
    assert store.get_clock_offset_seconds(fake_session_id) == 3600


def test_clock_offset_update_overwrites_not_duplicates(fake_session_id):
    store.set_clock_offset_seconds(fake_session_id, 100)
    store.set_clock_offset_seconds(fake_session_id, 200)
    assert store.get_clock_offset_seconds(fake_session_id) == 200


def test_clock_offset_is_isolated_between_two_sessions(fake_session_id):
    other_session_id = f"other-{fake_session_id}"
    store.set_clock_offset_seconds(fake_session_id, 500)
    store.set_clock_offset_seconds(other_session_id, 999)
    try:
        assert store.get_clock_offset_seconds(fake_session_id) == 500
        assert store.get_clock_offset_seconds(other_session_id) == 999
    finally:
        from app.db import get_session_factory
        from app.tables import ClockOffset

        Session = get_session_factory()
        with Session() as db:
            db.query(ClockOffset).filter(ClockOffset.session_id == other_session_id).delete()
            db.commit()


def test_save_and_get_journey_round_trips(fake_session_id):
    plan = _sample_plan()
    journey_id = store.save_journey(fake_session_id, plan)
    fetched = store.get_journey(fake_session_id, journey_id)
    assert fetched == plan


def test_get_journey_refuses_a_different_session(fake_session_id):
    plan = _sample_plan()
    journey_id = store.save_journey(fake_session_id, plan)

    other_session_id = f"other-{fake_session_id}"
    assert store.get_journey(other_session_id, journey_id) is None


def test_append_and_list_messages_round_trips(fake_session_id):
    store.append_message(fake_session_id, "user", "bangalore to varanasi 4th sept")
    store.append_message(fake_session_id, "agent", "Bengaluru has four stations...")

    messages = store.list_messages(fake_session_id)
    assert [m.content for m in messages] == [
        "bangalore to varanasi 4th sept",
        "Bengaluru has four stations...",
    ]


def test_messages_are_isolated_between_sessions(fake_session_id):
    other_session_id = f"other-{fake_session_id}"
    store.append_message(fake_session_id, "user", "hello from session A")
    store.append_message(other_session_id, "user", "hello from session B")
    try:
        a_messages = [m.content for m in store.list_messages(fake_session_id)]
        b_messages = [m.content for m in store.list_messages(other_session_id)]
        assert a_messages == ["hello from session A"]
        assert b_messages == ["hello from session B"]
    finally:
        from app.db import get_session_factory
        from app.tables import Message

        Session = get_session_factory()
        with Session() as db:
            db.query(Message).filter(Message.session_id == other_session_id).delete()
            db.commit()
