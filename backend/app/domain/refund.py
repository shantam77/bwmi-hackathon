"""Refund and cancellation-charge math. Pure Python -- no FastAPI, no
OpenAI, no ORM imports.

Ordinary cancellation tiers are modelled from published IRCTC guidance
(charge scales with how close to departure you cancel) -- sources vary on
exact percentages and minimums, so this is one consistent, documented set,
same disclosure pattern as domain/tdr.py. Flat minimums are per passenger."""

from datetime import datetime, timedelta

from app.models import RefundBreakdown

FLAT_MINIMUM_BY_CLASS = {"SL": 60, "3A": 200, "2A": 200, "1A": 240}
E_TICKET_SERVICE_CHARGE = 60  # docs/01-research-context-log.md section 5


def ordinary_cancellation_refund(
    fare_total: int,
    travel_class: str,
    passenger_count: int,
    now: datetime,
    scheduled_departure: datetime,
) -> RefundBreakdown:
    """What you get back for a normal (non-TDR) cancellation -- e.g. Flow
    H's leg 2, which IRCTC treats as an unrelated ticket with no
    connected-journey refund reason available."""
    time_to_departure = scheduled_departure - now
    flat_minimum = FLAT_MINIMUM_BY_CLASS.get(travel_class, 60) * passenger_count

    if time_to_departure >= timedelta(hours=48):
        charge = flat_minimum
        basis = "Cancelled 48h+ before departure: flat minimum charge."
    elif time_to_departure >= timedelta(hours=12):
        charge = max(flat_minimum, round(fare_total * 0.25))
        basis = "Cancelled 12-48h before departure: 25% of fare (or the minimum, whichever is higher)."
    elif time_to_departure >= timedelta(hours=4):
        charge = max(flat_minimum, round(fare_total * 0.5))
        basis = "Cancelled 4-12h before departure: 50% of fare (or the minimum, whichever is higher)."
    else:
        charge = fare_total
        basis = "Cancelled less than 4h before departure (or after): no refund under ordinary cancellation."

    charge = min(charge, fare_total)
    return RefundBreakdown(
        fare_total=fare_total, charge=charge, refund_amount=fare_total - charge, basis=basis
    )


def tdr_refund(fare_total: int, refund_basis: str) -> RefundBreakdown:
    """Applies a TDR reason code's refund_basis. Only full_fare and
    full_fare_auto are reachable by this build's flows (LATE_3H,
    TRAIN_CANCELLED, WAITLIST_NOT_CLEARED) -- the other bases exist in
    tdr_rules.json for completeness against the reason-code catalogue but
    aren't exercised by any flow yet. Rather than fabricate a specific
    partial calculation for those, this returns full fare with a labelled
    placeholder note -- see open_issues.md."""
    if refund_basis in ("full_fare", "full_fare_auto"):
        return RefundBreakdown(
            fare_total=fare_total, charge=0, refund_amount=fare_total, basis="Full fare refunded."
        )
    if refund_basis == "full_fare_minus_service_charge":
        charge = min(E_TICKET_SERVICE_CHARGE, fare_total)
        return RefundBreakdown(
            fare_total=fare_total,
            charge=charge,
            refund_amount=fare_total - charge,
            basis="Full fare minus the standard e-ticket service charge.",
        )
    return RefundBreakdown(
        fare_total=fare_total,
        charge=0,
        refund_amount=fare_total,
        basis=f"Refund basis '{refund_basis}' isn't modelled in detail yet -- showing full fare as a placeholder.",
    )
