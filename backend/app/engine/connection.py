"""Broken-connection detection and Flow H's four-system reasoning -- the
submission's flagship. Pure orchestration over app/domain: every figure in
the DecisionBlock traces to a domain function call below; the model only
composes the recommendation TEXT around what this hands it, never a number.

MIN_INTERCHANGE_MINUTES matches domain/search.py's own constant: a
connection search() accepted at booking time can still be broken later by a
delay large enough to eat that same buffer."""

from datetime import datetime, timedelta

from app import dataset
from app.domain import refund as refund_domain
from app.domain import search as search_domain
from app.domain import tdr as tdr_domain
from app.engine import state as state_engine
from app.models import DecisionBlockData, DecisionOption, JourneyStatus, PNRRecord

MIN_INTERCHANGE_MINUTES = search_domain.MIN_INTERCHANGE_MINUTES


def leg1_actual_arrival(leg1: PNRRecord, leg1_status: JourneyStatus) -> datetime:
    return state_engine.scheduled_arrival(leg1) + timedelta(minutes=leg1_status.delay_minutes)


def connection_is_broken(leg1: PNRRecord, leg1_status: JourneyStatus, leg2: PNRRecord) -> bool:
    """True when leg1's now-delayed arrival doesn't leave enough buffer to
    make leg2's scheduled departure -- the exact same buffer search() used
    when it originally offered this connection at booking time."""
    if leg1_status.is_cancelled:
        return True
    actual_arrival = leg1_actual_arrival(leg1, leg1_status)
    leg2_departure = state_engine.scheduled_departure(leg2)
    return (leg2_departure - actual_arrival) < timedelta(minutes=MIN_INTERCHANGE_MINUTES)


def find_rebooking_option(leg1: PNRRecord, leg1_status: JourneyStatus, leg2: PNRRecord):
    """The earliest other direct train on leg2's route, same class, with
    confirmed availability, that the passenger could actually still catch."""
    earliest_departure = leg1_actual_arrival(leg1, leg1_status) + timedelta(
        minutes=MIN_INTERCHANGE_MINUTES
    )
    candidates = []
    for plan in search_domain.search(
        leg2.from_station, leg2.to_station, leg2.date, leg2.travel_class
    ):
        if not plan.direct:
            continue
        candidate = plan.legs[0]
        if candidate.train_number == leg2.train_number or candidate.status != "AVAILABLE":
            continue
        candidate_departure = state_engine.combine_datetime(
            leg2.date, candidate.departure, candidate.departure_day_offset
        )
        if candidate_departure < earliest_departure:
            continue
        candidates.append((candidate, candidate_departure))

    if not candidates:
        return None
    candidates.sort(key=lambda pair: pair[1])
    return candidates[0][0]


def build_decision_block(
    leg1: PNRRecord, leg1_status: JourneyStatus, leg2: PNRRecord
) -> DecisionBlockData:
    now = datetime.fromisoformat(leg1_status.now_iso)
    leg2_departure = state_engine.scheduled_departure(leg2)

    # System 1: leg1 TDR eligibility.
    leg1_eligibility = tdr_domain.check_delay_eligibility(
        timedelta(minutes=leg1_status.delay_minutes), state_engine.scheduled_departure(leg1)
    )
    leg1_refund = (
        refund_domain.tdr_refund(leg1.total_fare, leg1_eligibility.refund_basis)
        if leg1_eligibility.eligible
        else refund_domain.RefundBreakdown(
            fare_total=leg1.total_fare, charge=leg1.total_fare, refund_amount=0, basis="Not yet TDR-eligible."
        )
    )

    # System 2: leg2 ordinary cancellation -- IRCTC has no connected-journey
    # refund reason, so this is treated as an unrelated ticket.
    leg2_refund = refund_domain.ordinary_cancellation_refund(
        leg2.total_fare, leg2.travel_class, len(leg2.passengers), now, leg2_departure
    )

    # System 3: retiring room auto-cancel. Phase 5 builds real retiring-room
    # bookings; none exists yet to cancel, so this system contributes ₹0 for
    # now rather than fabricate a booking that was never made -- see
    # open_issues.md.
    retiring_room_refund = 0

    option_1 = DecisionOption(
        name="Abandon both",
        items=[
            {
                "label": f"Leg 1 refund -- {leg1.train_number} {leg1.train_name}",
                "amount": leg1_refund.refund_amount,
                "note": leg1_eligibility.reason_label,
            },
            {
                "label": f"Leg 2 refund -- {leg2.train_number} {leg2.train_name}",
                "amount": leg2_refund.refund_amount,
                "note": leg2_refund.basis,
            },
            {"label": "Retiring room refund", "amount": retiring_room_refund, "note": "auto-cancels with the ticket"},
        ],
        deadline_iso=leg1_eligibility.deadline_iso,
        bottom_line_recovered=leg1_refund.refund_amount + leg2_refund.refund_amount + retiring_room_refund,
        bottom_line_total_paid=leg1.total_fare + leg2.total_fare,
    )

    # System 4: rebooking alternative.
    rebooking_leg = find_rebooking_option(leg1, leg1_status, leg2)
    if rebooking_leg is not None:
        rebooking_fare = rebooking_leg.fare_per_passenger * len(leg2.passengers)
        extra_cost = max(0, rebooking_fare - leg2_refund.refund_amount)
        option_2 = DecisionOption(
            name="Travel late, rebook leg 2",
            items=[
                {
                    "label": f"Cancel {leg2.train_number} {leg2.train_name}",
                    "amount": -leg2_refund.charge,
                    "note": leg2_refund.basis,
                },
                {
                    "label": f"Rebook {rebooking_leg.train_number} {rebooking_leg.train_name} ({rebooking_leg.departure})",
                    "amount": -rebooking_fare,
                    "note": None,
                },
            ],
            deadline_iso=None,
            bottom_line_recovered=0,
            bottom_line_total_paid=extra_cost,
        )
        recommendation = (
            f"I'd take Option 2. You lose ₹{extra_cost:,} instead of walking away from the trip "
            f"entirely, and you still reach {dataset.station_name(leg2.to_station)} today."
        )
    else:
        option_2 = DecisionOption(
            name="Travel late, rebook leg 2",
            items=[{"label": "No later train found with availability", "amount": 0, "note": None}],
            deadline_iso=None,
            bottom_line_recovered=0,
            bottom_line_total_paid=0,
        )
        recommendation = (
            "I'd take Option 1. There's no later train with seats available, so recovering "
            "what you can is the better move."
        )

    leg2_rule_explanation = (
        "IRCTC has no concept of a connected journey. Two tickets on two trains are two "
        "unrelated contracts. So when leg 1 is late, leg 2's railway hasn't done anything "
        "wrong -- no delay, no cancellation, no failure on their side. There's no refund "
        "reason that fits. You just cancel it like any other ticket and take the standard "
        "charge. This is one of the clearest gaps in how the system works. It costs people "
        "money on every missed connection in the country, and nothing in the current "
        "interface warns you before you book."
    )

    return DecisionBlockData(
        option_1=option_1,
        option_2=option_2,
        recommendation=recommendation,
        leg2_rule_explanation=leg2_rule_explanation,
    )
