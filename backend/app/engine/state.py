"""Journey status derivation and Demo Controls. Derives everything the alert
engine and gate table need from a PNR + the simulated clock, fresh every
time -- state is never stored independently (docs/04-implementation-plan.md
section 4.1). Not a rigid named-state enum; PDD section 8's gate table is
really a set of facts, and facts are what JourneyStatus models.

Demo Controls calibration note: the clock jumps these buttons produce are
chosen to reproduce docs/03-product-design-document.md's own worked numbers
exactly (3h20m delay, a 47-minute TDR countdown, "1h 5m late"). These are
demo SCENARIO PARAMETERS -- like the calibrated seed data in Phase 1 -- not
hardcoded business logic. The math consuming them (delay_minutes, TDR
eligibility, the deadline itself) is generic and works for any delay value,
not just these specific ones -- see open_issues.md if that ever needs
auditing again."""

from datetime import datetime, timedelta, timezone

from app import store
from app.domain import search as search_domain
from app.domain import tdr as tdr_domain
from app.domain import waitlist as waitlist_domain
from app.engine import clock
from app.models import JourneyStatus, Leg, PNRRecord

CHART_PREPARATION_HOURS_BEFORE = 4
BOARDING_DAY_HOURS_BEFORE = 1
DELAY_1H_MINUTES = 65  # matches PDD's "Running 1h 5m late"
DELAY_3H_MINUTES = 200  # 3h20m, matches PDD's "running 3h 20m late" exactly
DELAY_3H_COUNTDOWN_BUFFER_MINUTES = 47  # matches PDD's "47 minutes from now"
CANCELLED_MINUTES_AFTER_DEPARTURE = 10
CLEARANCE_PROBABILITY_THRESHOLD = 50.0  # deterministic demo outcome for a WL PNR at chart-prep

DEMO_STATES = ["chart_prepared", "boarding_day", "delay_1h", "delay_3h", "cancelled"]
DELAY_DEMO_STATE_MINUTES = {"delay_1h": DELAY_1H_MINUTES, "delay_3h": DELAY_3H_MINUTES}


def combine_datetime(date_str: str, time_str: str, day_offset: int = 0) -> datetime:
    """date_str is YYYY-MM-DD, time_str is HH:MM, day_offset shifts forward
    by whole days (e.g. an overnight arrival the day after departure)."""
    hour, minute = map(int, time_str.split(":"))
    year, month, day = map(int, date_str.split("-"))
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc) + timedelta(days=day_offset)


def scheduled_departure(pnr: PNRRecord) -> datetime:
    return combine_datetime(pnr.date, pnr.departure)


def scheduled_arrival(pnr: PNRRecord) -> datetime:
    return combine_datetime(pnr.date, pnr.arrival, pnr.arrival_day_offset)


def _find_current_leg(pnr: PNRRecord) -> Leg | None:
    for plan in search_domain.search(pnr.from_station, pnr.to_station, pnr.date, pnr.travel_class):
        if plan.direct and plan.legs[0].train_number == pnr.train_number:
            return plan.legs[0]
    return None


def apply_demo_state(session_id: str, pnr: PNRRecord, demo_state: str | None) -> None:
    """Jump this session's clock to the moment the named demo scenario
    represents, relative to the given PNR's scheduled departure."""
    if demo_state is None or demo_state == "reset":
        store.set_clock_offset_and_demo_state(session_id, 0, None)
        return
    if demo_state not in DEMO_STATES:
        raise ValueError(f"Unknown demo state: {demo_state}")

    departure = scheduled_departure(pnr)

    if demo_state == "chart_prepared":
        target = departure - timedelta(hours=CHART_PREPARATION_HOURS_BEFORE)
    elif demo_state == "boarding_day":
        target = departure - timedelta(hours=BOARDING_DAY_HOURS_BEFORE)
    elif demo_state == "delay_1h":
        target = departure + timedelta(minutes=DELAY_1H_MINUTES)
    elif demo_state == "delay_3h":
        actual_departure = departure + timedelta(minutes=DELAY_3H_MINUTES)
        target = actual_departure - timedelta(minutes=DELAY_3H_COUNTDOWN_BUFFER_MINUTES)
    else:  # cancelled
        target = departure + timedelta(minutes=CANCELLED_MINUTES_AFTER_DEPARTURE)

    offset_seconds = int((target - datetime.now(timezone.utc)).total_seconds())
    store.set_clock_offset_and_demo_state(session_id, offset_seconds, demo_state)


def compute_status(session_id: str, pnr: PNRRecord) -> JourneyStatus:
    now = clock.now(session_id)
    demo_state = store.get_demo_state(session_id)
    departure = scheduled_departure(pnr)

    is_cancelled = demo_state == "cancelled"
    chart_prepared = now >= departure - timedelta(hours=CHART_PREPARATION_HOURS_BEFORE)

    if is_cancelled:
        delay_minutes = 0
    elif demo_state in DELAY_DEMO_STATE_MINUTES:
        # The delay a demo button represents is a fact about the disruption
        # (what gets reported to the user), not "now minus scheduled
        # departure" -- "now" is deliberately set some minutes *before* the
        # delayed departure so there's a live countdown, so deriving delay
        # from elapsed wall-clock time here would silently undercount it.
        delay_minutes = DELAY_DEMO_STATE_MINUTES[demo_state]
    elif now > departure:
        # No delay demo state active, but wall-clock time has genuinely
        # passed the scheduled departure (e.g. real time simply advancing,
        # or a direct clock.jump_to() in a test) -- fall back to elapsed time.
        delay_minutes = int((now - departure).total_seconds() // 60)
    else:
        delay_minutes = 0

    cleared: bool | None = None
    effective_status = pnr.status
    if not is_cancelled and pnr.status == "WL":
        if chart_prepared:
            leg = _find_current_leg(pnr)
            if leg is not None:
                prediction = waitlist_domain.predict(leg.status, leg.quota, leg.seats_or_position)
                cleared = prediction.probability >= CLEARANCE_PROBABILITY_THRESHOLD
            else:
                cleared = False
            effective_status = "CNF" if cleared else "WL"
        # else: still WL, chart not prepared yet -- nothing to resolve
    elif pnr.status == "RAC":
        effective_status = "RAC"
    elif pnr.status == "AVAILABLE":
        effective_status = "CNF"

    chart_did_not_clear = (not is_cancelled) and pnr.status == "WL" and chart_prepared and cleared is False
    tdr_auto_refund = is_cancelled or chart_did_not_clear

    # Delegates the actual threshold/deadline math to domain/tdr.py rather
    # than re-encoding "3 hours" here -- one source of truth for the rule,
    # tested at second-precision boundaries in tests/test_tdr.py.
    tdr_eligible = False
    tdr_deadline_iso = None
    if not tdr_auto_refund and not is_cancelled:
        delay_eligibility = tdr_domain.check_delay_eligibility(
            timedelta(minutes=delay_minutes), departure
        )
        tdr_eligible = delay_eligibility.eligible
        tdr_deadline_iso = delay_eligibility.deadline_iso

    retiring_room_eligible = (not is_cancelled) and effective_status in ("CNF", "RAC")

    return JourneyStatus(
        pnr=pnr.pnr,
        demo_state=demo_state,
        now_iso=now.isoformat(),
        scheduled_departure_iso=departure.isoformat(),
        delay_minutes=delay_minutes,
        is_cancelled=is_cancelled,
        chart_prepared=chart_prepared,
        cleared=cleared,
        effective_status=effective_status,
        tdr_eligible=tdr_eligible,
        tdr_deadline_iso=tdr_deadline_iso,
        tdr_auto_refund=tdr_auto_refund,
        retiring_room_eligible=retiring_room_eligible,
    )
