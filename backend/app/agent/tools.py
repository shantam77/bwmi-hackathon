"""Thin @function_tool wrappers over app/domain and app/store. Every tool is
scoped by ctx.context.session_id -- no tool may read or write another
session's data. No business logic lives here; it's all in app/domain."""

from datetime import datetime, timedelta, timezone

from agents import RunContextWrapper, function_tool

from app import dataset, store
from app.agent.context import AgentContext
from app.domain import booking, catering, refund, retiring, search, stations, tdr, waitlist
from app.engine import clock, connection, state
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


MAX_SEARCH_OPTIONS = 3


def _plan_rank_key(described: dict) -> tuple:
    """Best-first ordering for the options a search returns to the model --
    domain/search.py itself stays exhaustive (every valid combination,
    unranked; that's correct for a pure function), so this is where a
    display-facing choice like "which 3 are worth showing" belongs. A
    connecting journey is only as reliable as its weakest leg, so rank by
    the lower of the two legs' confirmation odds first, then by the
    shorter layover as a tiebreaker."""
    min_probability = min(leg["waitlist_probability"] for leg in described["legs"])
    return (-min_probability, described["layover_minutes"] or 0)


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

    Returns at most 3 options: direct options if any exist between the
    resolved stations, otherwise the best single-interchange connecting
    options, ranked by each option's weakest leg's confirmation odds (then
    shortest layover) -- each leg booked separately, since IRCTC has no
    concept of a connected journey. Each leg carries a waitlist prediction.
    If a query name is ambiguous
    (e.g. "bangalore" matches four stations), `ambiguous_stations` names it
    and lists every candidate this tool already checked, each with its own
    name -- tell the user which stations you checked BY NAME, not by bare
    code (most people haven't memorized IRCTC's station codes), rather than
    asking them to pick one first.
    """
    from_resolution = stations.resolve(from_query)
    to_resolution = stations.resolve(to_query)

    if not from_resolution.matches:
        return {"error": f"'{from_query}' isn't a station I recognize."}
    if not to_resolution.matches:
        return {"error": f"'{to_query}' isn't a station I recognize."}

    def _candidates(resolution):
        return [{"code": m.station.code, "name": m.station.name} for m in resolution.matches]

    ambiguous_stations = []
    if from_resolution.ambiguous:
        ambiguous_stations.append({"query": from_query, "candidates": _candidates(from_resolution)})
    if to_resolution.ambiguous:
        ambiguous_stations.append({"query": to_query, "candidates": _candidates(to_resolution)})

    options = []
    for from_match in from_resolution.matches:
        for to_match in to_resolution.matches:
            plans = search.search(
                from_match.station.code, to_match.station.code, date, travel_class
            )
            options.extend(_describe_plan(p) for p in plans)

    options.sort(key=_plan_rank_key)
    options = options[:MAX_SEARCH_OPTIONS]

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
async def cancel_booking(ctx: RunContextWrapper[AgentContext], pnr: str) -> dict:
    """Cancel a PNR under ORDINARY cancellation rules -- the correct
    mechanism when the ticket's OWN train was never delayed or cancelled,
    so it isn't TDR-eligible. This is exactly Flow H's leg 2: the delay
    that broke the connection happened on a DIFFERENT, unrelated ticket:
    leg 2's own train is running fine, but the passenger can no longer
    use it. IRCTC has no connected-journey refund reason for that, so it's
    charged and refunded like any other voluntary cancellation -- never
    call file_tdr for a PNR whose own train wasn't delayed or cancelled.

    Reports the refund/charge breakdown; doesn't persist a claim record
    the way file_tdr does, since an ordinary cancellation is a same-day
    charge-and-refund, not a reviewed claim with a 45-day wait."""
    record = store.get_pnr(ctx.context.session_id, pnr)
    if record is None:
        return {"error": f"No booking found for PNR {pnr}."}

    session_id = ctx.context.session_id
    now = clock.now(session_id)
    departure = state.scheduled_departure(record)
    breakdown = refund.ordinary_cancellation_refund(
        record.total_fare, record.travel_class, len(record.passengers), now, departure
    )
    return {
        "pnr": pnr,
        "fare_total": breakdown.fare_total,
        "charge": breakdown.charge,
        "refund_amount": breakdown.refund_amount,
        "basis": breakdown.basis,
    }


@function_tool
async def get_flow_h_rebooking_option(ctx: RunContextWrapper[AgentContext], leg2_pnr: str) -> dict:
    """After the user chooses a DecisionBlock's "Travel late, rebook leg 2"
    option, call this to get the EXACT replacement train the DecisionBlock
    itself computed and displayed. The DecisionBlock is rendered directly
    by the backend, not produced by a tool call -- you have no other way
    to see which specific train it named. Reuses the identical selection
    logic (engine.connection.find_rebooking_option) so this always matches
    what the user was actually shown; never independently call
    search_trains and pick a substitute, it may not be the same train.
    Pass leg2_pnr = the PNR being replaced (the one cancel_booking was
    just called on)."""
    leg2 = store.get_pnr(ctx.context.session_id, leg2_pnr)
    if leg2 is None:
        return {"error": f"No booking found for PNR {leg2_pnr}."}
    if not leg2.linked_pnr:
        return {"error": f"PNR {leg2_pnr} isn't linked to another leg -- there's no Flow H rebooking for it."}
    leg1 = store.get_pnr(ctx.context.session_id, leg2.linked_pnr)
    if leg1 is None:
        return {"error": f"Linked leg PNR {leg2.linked_pnr} not found."}

    session_id = ctx.context.session_id
    leg1_status = state.compute_status(session_id, leg1)
    candidate = connection.find_rebooking_option(leg1, leg1_status, leg2)
    if candidate is None:
        return {"error": "No rebooking option is currently available for this leg."}
    return {
        "train_number": candidate.train_number,
        "train_name": candidate.train_name,
        "from_station": candidate.from_station,
        "to_station": candidate.to_station,
        "date": leg2.date,
        "departure": candidate.departure,
        "travel_class": candidate.travel_class,
        "fare_per_passenger": candidate.fare_per_passenger,
    }


@function_tool
async def get_refund_status(ctx: RunContextWrapper[AgentContext], pnr: str) -> dict:
    """Look up the status of a previously filed TDR claim for a PNR."""
    claim = store.get_tdr_claim(ctx.context.session_id, pnr)
    if claim is None:
        return {"error": f"No TDR claim on file for PNR {pnr}."}
    return claim.model_dump()


def _resolve_station_code(query: str) -> str:
    """Best-effort station name/alias -> code resolution for tools that
    match against an exact code (a train's schedule, a facility list).
    Falls back to the raw query if nothing resolves, so an unrecognized
    string still fails with a clear "not on this route" error downstream
    rather than a resolution error here. Unlike search_trains, true
    ambiguity isn't handled specially -- these tools operate against one
    specific, already-booked train's route, so the best-scoring match is
    either the right station or the lookup correctly fails anyway."""
    resolution = stations.resolve(query)
    if not resolution.matches:
        return query
    return resolution.matches[0].station.code


def _minutes_until_arrival(pnr_record, station_code: str, session_id: str) -> int | None:
    """Minutes from the session's simulated now until the booked train
    reaches station_code along its own route. None if that station isn't on
    this train's schedule. Computed here, not trusted from the model --
    same lesson as Flow H's date-derivation fix."""
    stops = dataset.schedule_for_train(pnr_record.train_number)
    stop = next((s for s in stops if s.station_code == station_code), None)
    if stop is None or stop.arrival is None:
        return None
    arrival_dt = state.combine_datetime(pnr_record.date, stop.arrival, stop.day_offset)
    now = clock.now(session_id)
    return int((arrival_dt - now).total_seconds() // 60)


@function_tool
async def get_catering_options(ctx: RunContextWrapper[AgentContext], pnr: str, station: str) -> dict:
    """Catering vendors at an upcoming halt station that can actually
    deliver in time, filtered by the real halt timing on this booked
    train's own schedule. Reports how many others were hidden because they
    can't make the cutoff -- that filtering is the point. station can be a
    station code, city name, or common alias -- resolution happens inside
    this tool, same as search_trains."""
    record = store.get_pnr(ctx.context.session_id, pnr)
    if record is None:
        return {"error": f"No booking found for PNR {pnr}."}
    station_code = _resolve_station_code(station)
    minutes = _minutes_until_arrival(record, station_code, ctx.context.session_id)
    if minutes is None:
        return {"error": f"{station} isn't a stop on {record.train_number}'s route."}
    vendors, hidden_count = catering.available_vendors(station_code, minutes)
    return {
        "station": station_code,
        "minutes_until_arrival": minutes,
        "vendors": [v.model_dump() for v in vendors],
        "hidden_count": hidden_count,
    }


@function_tool
async def get_retiring_room_availability(
    ctx: RunContextWrapper[AgentContext], pnr: str, station: str
) -> dict:
    """Retiring room options at a station, gated on the PNR's current
    status -- waitlisted tickets never see an offer, matching the real
    rr.irctc.co.in rule. station can be a station code, city name, or
    common alias -- resolution happens inside this tool, same as
    search_trains."""
    record = store.get_pnr(ctx.context.session_id, pnr)
    if record is None:
        return {"error": f"No booking found for PNR {pnr}."}
    station_code = _resolve_station_code(station)
    status = state.compute_status(ctx.context.session_id, record)
    options = retiring.room_options(station_code, status.effective_status)
    return {
        "station": station_code,
        "eligible": status.effective_status in retiring.ELIGIBLE_STATUSES,
        "effective_status": status.effective_status,
        "options": [o.model_dump() for o in options],
    }


@function_tool
async def book_retiring_room(
    ctx: RunContextWrapper[AgentContext], pnr: str, station: str, room_type: str
) -> dict:
    """Book a retiring room for a PNR. Only call this after
    get_retiring_room_availability confirmed eligible=true and the user
    picked a specific room_type. This is a demo booking -- no money moves,
    and (unlike train PNRs) it isn't persisted for later lookup. station
    can be a station code, city name, or common alias -- resolution
    happens inside this tool, same as search_trains."""
    record = store.get_pnr(ctx.context.session_id, pnr)
    if record is None:
        return {"error": f"No booking found for PNR {pnr}."}
    station_code = _resolve_station_code(station)
    status = state.compute_status(ctx.context.session_id, record)
    options = retiring.room_options(station_code, status.effective_status)
    match = next((o for o in options if o.room_type == room_type), None)
    if match is None:
        return {"error": f"No available '{room_type}' room at {station} for this PNR."}
    return {
        "booking_reference": booking.generate_pnr(),
        "station": station_code,
        "room_type": match.room_type,
        "tariff": match.tariff,
        "note": "Demo booking -- no money moves.",
    }


ALL_TOOLS = [
    search_trains,
    quote_booking,
    confirm_booking,
    get_pnr_status,
    check_tdr_eligibility,
    file_tdr,
    cancel_booking,
    get_flow_h_rebooking_option,
    get_refund_status,
    get_catering_options,
    get_retiring_room_availability,
    book_retiring_room,
]
