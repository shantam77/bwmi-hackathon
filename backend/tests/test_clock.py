from datetime import datetime, timedelta, timezone

from app.engine import clock
from tests.conftest import requires_db

pytestmark = requires_db

# Every clock.now()/jump_to() call round-trips to Postgres over Railway's
# public proxy, which can add a couple of real seconds of latency. These
# tests check clock correctness (does the offset move the right amount),
# not sub-second precision, so the tolerance is generous on purpose.
TOLERANCE_SECONDS = 8


def test_now_is_close_to_real_time_with_no_offset(fake_session_id):
    before = datetime.now(timezone.utc)
    result = clock.now(fake_session_id)
    after = datetime.now(timezone.utc)
    assert before - timedelta(seconds=TOLERANCE_SECONDS) <= result <= after + timedelta(
        seconds=TOLERANCE_SECONDS
    )


def test_jump_to_moves_now_to_the_target(fake_session_id):
    target = datetime.now(timezone.utc) + timedelta(hours=3, minutes=20)
    clock.jump_to(fake_session_id, target)
    result = clock.now(fake_session_id)
    assert abs((result - target).total_seconds()) < TOLERANCE_SECONDS


def test_advance_by_shifts_from_the_current_offset(fake_session_id):
    clock.jump_to(fake_session_id, datetime.now(timezone.utc) + timedelta(hours=1))
    clock.advance_by(fake_session_id, timedelta(hours=2))
    result = clock.now(fake_session_id)
    expected = datetime.now(timezone.utc) + timedelta(hours=3)
    assert abs((result - expected).total_seconds()) < TOLERANCE_SECONDS


def test_reset_returns_to_real_time(fake_session_id):
    clock.jump_to(fake_session_id, datetime.now(timezone.utc) + timedelta(days=1))
    clock.reset(fake_session_id)
    result = clock.now(fake_session_id)
    assert abs((result - datetime.now(timezone.utc)).total_seconds()) < TOLERANCE_SECONDS


def test_two_sessions_have_independent_clocks(fake_session_id):
    other_session_id = f"other-{fake_session_id}"
    clock.jump_to(fake_session_id, datetime.now(timezone.utc) + timedelta(hours=3))
    try:
        a_now = clock.now(fake_session_id)
        b_now = clock.now(other_session_id)
        # Session B never jumped -- must still read close to real time, not
        # session A's +3h offset. This is the isolation bug the plan calls
        # out as most likely to silently ruin Stage 1 review.
        assert (a_now - b_now).total_seconds() > 3 * 60 * 60 - TOLERANCE_SECONDS
    finally:
        from app.db import get_session_factory
        from app.tables import ClockOffset

        Session = get_session_factory()
        with Session() as db:
            db.query(ClockOffset).filter(ClockOffset.session_id == other_session_id).delete()
            db.commit()
