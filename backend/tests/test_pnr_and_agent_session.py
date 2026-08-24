from app import store
from app.models import PassengerInput
from tests.conftest import requires_db

pytestmark = requires_db


def test_create_and_get_pnr_round_trips(fake_session_id):
    passengers = [PassengerInput(name="Shantam", age=27), PassengerInput(name="Ravi", age=61, berth_preference="lower")]
    store.create_pnr(
        session_id=fake_session_id,
        pnr_number="8429516703",
        train_number="12295",
        train_name="Sanghamitra Express",
        from_station="SBC",
        to_station="NGP",
        date="2026-09-04",
        departure="20:00",
        arrival="06:15",
        arrival_day_offset=1,
        travel_class="SL",
        status="WL",
        fare_total=1240,
        passengers=passengers,
    )

    record = store.get_pnr(fake_session_id, "8429516703")
    assert record is not None
    assert record.pnr == "8429516703"
    assert record.train_number == "12295"
    assert record.total_fare == 1240
    assert {p.name for p in record.passengers} == {"Shantam", "Ravi"}


def test_get_pnr_refuses_a_different_session(fake_session_id):
    store.create_pnr(
        session_id=fake_session_id,
        pnr_number="1111111111",
        train_number="12295",
        train_name="Sanghamitra Express",
        from_station="SBC",
        to_station="NGP",
        date="2026-09-04",
        departure="20:00",
        arrival="06:15",
        arrival_day_offset=1,
        travel_class="SL",
        status="WL",
        fare_total=620,
        passengers=[PassengerInput(name="Solo", age=30)],
    )
    other_session_id = f"other-{fake_session_id}"
    assert store.get_pnr(other_session_id, "1111111111") is None


def test_get_pnr_returns_none_for_unknown_pnr(fake_session_id):
    assert store.get_pnr(fake_session_id, "0000000000") is None


def test_agent_session_items_round_trip_in_order(fake_session_id):
    store.add_agent_session_items(fake_session_id, [{"role": "user", "content": "hi"}])
    store.add_agent_session_items(fake_session_id, [{"role": "assistant", "content": "hello"}])

    items = store.get_agent_session_items(fake_session_id)
    assert items == [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]


def test_agent_session_items_are_isolated_between_sessions(fake_session_id):
    other_session_id = f"other-{fake_session_id}"
    store.add_agent_session_items(fake_session_id, [{"role": "user", "content": "A"}])
    store.add_agent_session_items(other_session_id, [{"role": "user", "content": "B"}])
    try:
        assert store.get_agent_session_items(fake_session_id) == [{"role": "user", "content": "A"}]
        assert store.get_agent_session_items(other_session_id) == [{"role": "user", "content": "B"}]
    finally:
        store.clear_agent_session(other_session_id)


def test_pop_agent_session_item_removes_the_most_recent(fake_session_id):
    store.add_agent_session_items(
        fake_session_id, [{"content": "first"}, {"content": "second"}]
    )
    popped = store.pop_agent_session_item(fake_session_id)
    assert popped == {"content": "second"}
    assert store.get_agent_session_items(fake_session_id) == [{"content": "first"}]


def test_pop_agent_session_item_returns_none_when_empty(fake_session_id):
    assert store.pop_agent_session_item(fake_session_id) is None


def test_clear_agent_session_removes_everything(fake_session_id):
    store.add_agent_session_items(fake_session_id, [{"content": "x"}])
    store.clear_agent_session(fake_session_id)
    assert store.get_agent_session_items(fake_session_id) == []
