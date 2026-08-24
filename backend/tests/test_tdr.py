from datetime import datetime, timedelta, timezone

from app.domain import tdr

DEPARTURE = datetime(2026, 9, 4, 20, 0, tzinfo=timezone.utc)
ARRIVAL = datetime(2026, 9, 5, 6, 15, tzinfo=timezone.utc)


def test_delay_at_2h59m59s_is_not_eligible():
    result = tdr.check_delay_eligibility(timedelta(hours=2, minutes=59, seconds=59), DEPARTURE)
    assert result.eligible is False
    assert result.reason_code is None


def test_delay_at_exactly_3h_is_eligible():
    result = tdr.check_delay_eligibility(timedelta(hours=3), DEPARTURE)
    assert result.eligible is True


def test_delay_at_3h00m01s_is_eligible():
    result = tdr.check_delay_eligibility(timedelta(hours=3, seconds=1), DEPARTURE)
    assert result.eligible is True
    assert result.reason_code == "LATE_3H"


def test_delay_eligibility_deadline_is_the_actual_delayed_departure():
    delay = timedelta(hours=3, minutes=20)
    result = tdr.check_delay_eligibility(delay, DEPARTURE)
    assert result.deadline_iso == (DEPARTURE + delay).isoformat()
    assert result.auto_refund is False
    assert result.needs_certificate is False


def test_cancellation_is_auto_refund_never_eligible_for_filing():
    result = tdr.check_cancellation_eligibility()
    assert result.eligible is False
    assert result.auto_refund is True
    assert result.reason_code == "TRAIN_CANCELLED"
    assert result.deadline_iso is None  # no time limit


def test_waitlist_not_cleared_is_auto_refund_never_eligible_for_filing():
    result = tdr.check_waitlist_not_cleared_eligibility()
    assert result.eligible is False
    assert result.auto_refund is True
    assert result.reason_code == "WAITLIST_NOT_CLEARED"


def test_general_case_at_71h59m_is_eligible():
    now = ARRIVAL + timedelta(hours=71, minutes=59)
    result = tdr.check_general_eligibility(now, ARRIVAL)
    assert result.eligible is True
    assert result.reason_code == "GENERAL"


def test_general_case_at_exactly_72h_is_eligible():
    now = ARRIVAL + timedelta(hours=72)
    result = tdr.check_general_eligibility(now, ARRIVAL)
    assert result.eligible is True


def test_general_case_at_72h01m_is_not_eligible():
    now = ARRIVAL + timedelta(hours=72, minutes=1)
    result = tdr.check_general_eligibility(now, ARRIVAL)
    assert result.eligible is False
    assert result.reason_code is None


def test_downgrade_within_3h_of_actual_departure_is_eligible():
    actual_departure = DEPARTURE + timedelta(minutes=45)
    now = actual_departure + timedelta(hours=2, minutes=59)
    result = tdr.check_downgrade_eligibility(now, actual_departure)
    assert result.eligible is True
    assert result.reason_code == "CLASS_DOWNGRADE"
    assert result.needs_certificate is True


def test_downgrade_after_3h_of_actual_departure_is_not_eligible():
    actual_departure = DEPARTURE + timedelta(minutes=45)
    now = actual_departure + timedelta(hours=3, minutes=1)
    result = tdr.check_downgrade_eligibility(now, actual_departure)
    assert result.eligible is False
