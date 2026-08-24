from datetime import datetime, timedelta, timezone

from app.domain import refund

DEPARTURE = datetime(2026, 9, 5, 8, 40, tzinfo=timezone.utc)


def test_cancel_more_than_48h_before_charges_only_flat_minimum():
    now = DEPARTURE - timedelta(hours=49)
    result = refund.ordinary_cancellation_refund(1890, "SL", 2, now, DEPARTURE)
    assert result.charge == refund.FLAT_MINIMUM_BY_CLASS["SL"] * 2  # 120
    assert result.refund_amount == 1890 - 120


def test_cancel_between_12h_and_48h_charges_25_percent_or_minimum():
    now = DEPARTURE - timedelta(hours=24)
    result = refund.ordinary_cancellation_refund(1890, "SL", 2, now, DEPARTURE)
    assert result.charge == round(1890 * 0.25)
    assert result.refund_amount == 1890 - round(1890 * 0.25)


def test_cancel_between_4h_and_12h_charges_50_percent_or_minimum():
    now = DEPARTURE - timedelta(hours=6)
    result = refund.ordinary_cancellation_refund(1890, "SL", 2, now, DEPARTURE)
    assert result.charge == round(1890 * 0.5)


def test_cancel_less_than_4h_before_gets_no_refund():
    now = DEPARTURE - timedelta(hours=1)
    result = refund.ordinary_cancellation_refund(1890, "SL", 2, now, DEPARTURE)
    assert result.charge == 1890
    assert result.refund_amount == 0


def test_cancel_after_departure_gets_no_refund():
    now = DEPARTURE + timedelta(minutes=5)
    result = refund.ordinary_cancellation_refund(1890, "SL", 2, now, DEPARTURE)
    assert result.refund_amount == 0


def test_charge_never_exceeds_fare_total_even_for_a_tiny_fare():
    now = DEPARTURE - timedelta(hours=6)  # 50% tier
    result = refund.ordinary_cancellation_refund(100, "3A", 1, now, DEPARTURE)
    # flat minimum for 3A (200) would exceed the fare -- must be capped.
    assert result.charge == 100
    assert result.refund_amount == 0


def test_tdr_full_fare_basis_is_a_complete_refund():
    result = refund.tdr_refund(1240, "full_fare")
    assert result.refund_amount == 1240
    assert result.charge == 0


def test_tdr_full_fare_auto_basis_is_also_a_complete_refund():
    result = refund.tdr_refund(1240, "full_fare_auto")
    assert result.refund_amount == 1240


def test_tdr_minus_service_charge_basis_deducts_exactly_60():
    result = refund.tdr_refund(1240, "full_fare_minus_service_charge")
    assert result.charge == 60
    assert result.refund_amount == 1180


def test_tdr_unmodelled_basis_falls_back_to_full_fare_with_a_labelled_placeholder():
    result = refund.tdr_refund(1240, "proportionate_fare")
    assert result.refund_amount == 1240
    assert "not" in result.basis.lower() or "placeholder" in result.basis.lower()
