"""Thin @function_tool wrappers over app/domain and app/store. Every tool is
scoped by ctx.context.session_id -- no tool may read or write another
session's data. No business logic lives here; it's all in app/domain."""

from datetime import datetime, timedelta, timezone

from agents import RunContextWrapper, function_tool

from app import store
from app.agent.context import AgentContext
from app.domain import booking, refund, search, stations, tdr, waitlist
from app.engine import clock, state
from app.models import BookingConfirmation, JourneyPlan, Leg, PassengerInput


def _describe_leg(leg: Leg) -> dict:
    prediction = waitlist.predict(leg.status, leg.quota, leg.seats_or_position)
    return {
        "train_number": leg.train_number,
        "train_name": leg.train_name,
        "from_station": leg.from_station,
        "to_station": leg.to_station,
        "departure": leg.departure,
        "arrival": leg.arrival,
        "departure_day_offset": leg.departure_day_offset,
        "arrival_day_offset": leg.arrival_day_offset,
        "travel_class": leg.travel_class,
        "status": leg.status,
        "seats_or_position": leg.seats_or_position,
        "fare_per_passenger": leg.fare_per_passenger,
        "waitlist_band": prediction.band,
        "waitlist_probability": prediction.probability,
        "waitlist_type": prediction.waitlist_type,
        "waitlist_explanation": prediction.explanation,
    }


def _describe_plan(plan: JourneyPlan) -> dict:
    return {
        "direct": plan.direct,
        "interchange": plan.interchange,
        "layover_minutes": plan.layover_minutes,
        "legs": [_describe_leg(leg) for leg in plan.legs],
    }


@function_tool
async def search_trains(
    ctx: RunContextWrapper[AgentContext],
    from_query: str,
    to_query: str,
    date: str,
    travel_class: str = "SL",
) -> dict:
    """Search for trains between two places on a given date.

    from_query and to_query can be a station code, city name, or common
    alias (e.g. "bangalore", "varanasi") -- resolution and disambiguation
    happen inside this tool. date is YYYY-MM-DD. travel_class is one of
    SL/3A/2A/1A.

    Returns direct options if any exist between the resolved stations,
    otherwise the best single-interchange connecting options -- each leg
    booked separately, since IRCTC has no concept of a connected journey.
    Each leg carries a waitlist prediction. If a query name is ambiguous
    (e.g. "bangalore" matches four stations), `ambiguous_stations` names it
    and lists every candidate this tool already checked -- tell the user
    which stations you checked rather than asking them to pick one first.
    """
    from_resolution = stations.resolve(from_query)
    to_resolution = stations.resolve(to_query)

    if not from_resolution.matches:
        return {"error": f"'{from_query}' isn't a station I recognize."}
    if not to_resolution.matches:
        return {"error": f"'{to_query}' isn't a station I recognize."}

    ambiguous_stations = []
    if from_resolution.ambiguous:
        ambiguous_stations.append(
            {"query": from_query, "candidates": [m.station.code for m in from_resolution.matches]}
        )
    if to_resolution.ambiguous:
        ambiguous_stations.append(
            {"query": to_query, "candidates": [m.station.code for m in to_resolution.matches]}
        )

    options = []
    for from_match in from_resolution.matches:
        for to_match in to_resolution.matches:
            plans = search.search(
                from_match.station.code, to_match.station.code, date, travel_class
            )
            options.extend(_describe_plan(p) for p in plans)

    return {"ambiguous_stations": ambiguous_stations, "options": options}


def _find_leg(
    train_number: str, from_station: str, to_station: str, date: str, travel_class: str
) -> Leg | None:
    for plan in search.search(from_station, to_station, date, travel_class):
        if plan.direct and plan.legs[0].train_number == train_number:
            return plan.legs[0]
    return None


@function_tool
async def quote_booking(
    ctx: RunContextWrapper[AgentContext],
    train_number: str,
    from_station: str,
    to_station: str,
    date: str,
    travel_class: str,
    passengers: list[PassengerInput],
) -> dict:
    """Get a fare quote for specific passengers on a specific train, found
    via search_trains. from_station/to_station must be that LEG's own
    from/to (e.g. SBC/NGP for leg 1 of a connecting journey), not the
    overall trip's endpoints -- each leg is booked and paid for separately.

    Applies the senior-citizen lower-berth preference automatically (age
    >= 60). This does NOT create a booking -- present the total fare to the
    user as a payment step, and only call confirm_booking with the same
    arguments after they've confirmed payment.
    """
    leg = _find_leg(train_number, from_station, to_station, date, travel_class)
    if leg is None:
        return {
            "error": (
                f"No current {travel_class} option found for train {train_number} "
                f"from {from_station} to {to_station} on {date}."
            )
        }
    result = booking.quote(
        train_number=leg.train_number,
        train_name=leg.train_name,
        from_station=leg.from_station,
        to_station=leg.to_station,
        date=date,
        travel_class=leg.travel_class,
        status=leg.status,
        seats_or_position=leg.seats_or_position,
        fare_per_passenger=leg.fare_per_passenger,
        passengers=passengers,
    )
    return result.model_dump()


@function_tool
async def confirm_booking(
    ctx: RunContextWrapper[AgentContext],
    train_number: str,
    from_station: str,
    to_station: str,
    date: str,
    travel_class: str,
    passengers: list[PassengerInput],
    linked_pnr: str | None = None,
) -> dict:
    """Finalize a booking after the user has explicitly confirmed the mock
    payment for a quote_booking result with the same arguments. Creates the
    PNR and returns the confirmation. Never call this on the strength of a
    quote alone -- only after the user has confirmed payment.

    Pass linked_pnr = the OTHER leg's PNR number when this booking is the
    second leg of a connecting journey you already showed the user together
    (e.g. via search_trains' connecting options) -- this is what lets the
    app later reason across both tickets if the connection breaks (Flow H).
    Leave it out for a standalone single-leg booking.
    """
    leg = _find_leg(train_number, from_station, to_station, date, travel_class)
    if leg is None:
        return {
            "error": (
                f"No current {travel_class} option found for train {train_number} "
                f"from {from_station} to {to_station} on {date}."
            )
        }

    linked_record = None
    if linked_pnr:
        linked_record = store.get_pnr(ctx.context.session_id, linked_pnr)
        if linked_record is None:
            return {"error": f"No booking found for PNR {linked_pnr} to link this to."}
        # Derive this leg's calendar date from the linked leg's own arrival
        # rather than trust the date argument -- a connecting leg's date is
        # a fact about the first leg's schedule (when it actually gets you
        # to the interchange), not something to compute from scratch. An
        # agent getting this arithmetic wrong (e.g. reusing leg 1's date)
        # would otherwise silently corrupt every downstream calendar
        # calculation for this PNR, found via live testing.
        date = state.scheduled_arrival(linked_record).date().isoformat()

    result = booking.quote(
        train_number=leg.train_number,
        train_name=leg.train_name,
        from_station=leg.from_station,
        to_station=leg.to_station,
        date=date,
        travel_class=leg.travel_class,
        status=leg.status,
        seats_or_position=leg.seats_or_position,
        fare_per_passenger=leg.fare_per_passenger,
        passengers=passengers,
    )

    pnr_number = booking.generate_pnr()
    store.create_pnr(
        session_id=ctx.context.session_id,
        pnr_number=pnr_number,
        train_number=leg.train_number,
        train_name=leg.train_name,
        from_station=leg.from_station,
        to_station=leg.to_station,
        date=date,
        departure=leg.departure,
        arrival=leg.arrival,
        arrival_day_offset=leg.arrival_day_offset,
        travel_class=leg.travel_class,
        status=leg.status,
        fare_total=result.total_fare,
        passengers=result.passengers,
        linked_pnr=linked_pnr,
    )
    confirmation = BookingConfirmation(
        pnr=pnr_number,
        train_number=leg.train_number,
        train_name=leg.train_name,
        departure=leg.departure,
        date=date,
        travel_class=leg.travel_class,
        status=leg.status,
        passengers=result.passengers,
        total_fare=result.total_fare,
    )
    return confirmation.model_dump()


@function_tool
async def get_pnr_status(ctx: RunContextWrapper[AgentContext], pnr: str) -> dict:
    """Look up a previously booked PNR's status for the current session."""
    record = store.get_pnr(ctx.context.session_id, pnr)
    if record is None:
        return {"error": f"No booking found for PNR {pnr}."}
    return record.model_dump()


@function_tool
async def check_tdr_eligibility(ctx: RunContextWrapper[AgentContext], pnr: str) -> dict:
    """Check whether a booked PNR is currently eligible to file a TDR
    (refund claim), and if so, the reason code, deadline and refund basis.
    Also reports the auto-refund cases where filing is unnecessary."""
    record = store.get_pnr(ctx.context.session_id, pnr)
    if record is None:
        return {"error": f"No booking found for PNR {pnr}."}

    session_id = ctx.context.session_id
    status = state.compute_status(session_id, record)

    if status.is_cancelled:
        eligibility = tdr.check_cancellation_eligibility()
    elif status.tdr_auto_refund:
        eligibility = tdr.check_waitlist_not_cleared_eligibility()
    else:
        eligibility = tdr.check_delay_eligibility(
            timedelta(minutes=status.delay_minutes),
            state.scheduled_departure(record),
        )
    return {"pnr": pnr, "delay_minutes": status.delay_minutes, **eligibility.model_dump()}


@function_tool
async def file_tdr(ctx: RunContextWrapper[AgentContext], pnr: str) -> dict:
    """File a TDR for a booked PNR. Only call this after check_tdr_eligibility
    confirms eligible=True and the user has explicitly asked to file -- never
    on a cancelled or auto-refund PNR (there's nothing to file)."""
    record = store.get_pnr(ctx.context.session_id, pnr)
    if record is None:
        return {"error": f"No booking found for PNR {pnr}."}

    session_id = ctx.context.session_id
    status = state.compute_status(session_id, record)
    if status.is_cancelled or status.tdr_auto_refund:
        return {
            "error": (
                "This PNR auto-refunds -- there's nothing to file. "
                "Call check_tdr_eligibility for the details."
            )
        }

    eligibility = tdr.check_delay_eligibility(
        timedelta(minutes=status.delay_minutes), state.scheduled_departure(record)
    )
    if not eligibility.eligible:
        return {"error": "Not TDR-eligible yet -- delay hasn't crossed 3 hours."}

    breakdown = refund.tdr_refund(record.total_fare, eligibility.refund_basis)
    claim = store.file_tdr_claim(
        session_id=session_id,
        pnr=pnr,
        reason_code=eligibility.reason_code,
        reason_label=eligibility.reason_label,
        refund_amount=breakdown.refund_amount,
    )
    return claim.model_dump()


@function_tool
async def get_refund_status(ctx: RunContextWrapper[AgentContext], pnr: str) -> dict:
    """Look up the status of a previously filed TDR claim for a PNR."""
    claim = store.get_tdr_claim(ctx.context.session_id, pnr)
    if claim is None:
        return {"error": f"No TDR claim on file for PNR {pnr}."}
    return claim.model_dump()


ALL_TOOLS = [
    search_trains,
    quote_booking,
    confirm_booking,
    get_pnr_status,
    check_tdr_eligibility,
    file_tdr,
    get_refund_status,
]
