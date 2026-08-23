"""Deterministic alert rules -- the model NEVER decides whether to alert; it
only phrases the alert marked requires_reasoning (D8, once Phase 4 wires in
real TDR figures). Everything else renders from a template with no model
call. See PDD Flow D (D1-D11).

Reachability, disclosed rather than hidden: D5 (halt-approaching/catering)
and D10 (approaching destination) need a live mid-journey position -- the
six Demo Controls buttons cover chart-prep through cancellation, not
"currently en route." Their rule functions exist for completeness against
the PDD's catalogue but never fire in this build. D7 (connection at risk)
and D11 (refund status change) need Phase 4's two-leg journey tracking and
TDR claims respectively -- wired in then. Logged in open_issues.md."""

import hashlib
from dataclasses import dataclass, field

from app import store
from app.models import JourneyStatus, PNRRecord

SEVERITY_INFO = "info"  # blue
SEVERITY_WARN = "warn"  # yellow
SEVERITY_CRITICAL = "critical"  # red

DELAY_1H_THRESHOLD_MINUTES = 60
TDR_DELAY_THRESHOLD_MINUTES = 180


@dataclass
class Alert:
    alert_id: str
    severity: str
    message: str
    action: str | None
    requires_reasoning: bool
    dedup_key: str
    payload: dict = field(default_factory=dict)


def _synthetic_seat(pnr_number: str) -> tuple[str, int, int]:
    """Deterministic, stable-per-PNR coach/berth so D2's message doesn't
    have to invent a new one every time it's computed. Synthetic like
    everything else in this dataset -- disclosed via the honesty panel."""
    digest = hashlib.sha256(pnr_number.encode()).hexdigest()
    coach = f"S{1 + int(digest[:2], 16) % 8}"
    berth_a = 1 + int(digest[2:4], 16) % 70
    berth_b = berth_a + 1
    return coach, berth_a, berth_b


def _synthetic_platform(train_number: str) -> int:
    digest = hashlib.sha256(train_number.encode()).hexdigest()
    return 1 + int(digest[:2], 16) % 10


def evaluate(session_id: str, pnr: PNRRecord, status: JourneyStatus) -> list[Alert]:
    """Run every rule, skip already-fired ones (deduped on alert_id +
    dedup_key), persist and return newly fired alerts in priority order."""
    candidates = [
        _d1_waitlist_improved(pnr, status),
        _d2_d3_chart_prepared(pnr, status),
        _d4_platform_assigned(pnr, status),
        _d6_delay_crosses_1h(pnr, status),
        _d8_delay_crosses_3h(pnr, status),
        _d9_retiring_room_bookable(pnr, status),
    ]
    fresh = []
    for alert in candidates:
        if alert is None:
            continue
        if store.has_fired(session_id, pnr.pnr, alert.alert_id, alert.dedup_key):
            continue
        store.record_fired(
            session_id, pnr.pnr, alert.alert_id, alert.severity, alert.dedup_key, alert.payload
        )
        fresh.append(alert)
    return fresh


def _d1_waitlist_improved(pnr: PNRRecord, status: JourneyStatus) -> Alert | None:
    # Simulated: there's no time-varying waitlist dataset to trend against,
    # so this fires once on "boarding_day" for a still-WL ticket, showing a
    # generic (position // 2) improvement -- documented in open_issues.md.
    if status.demo_state != "boarding_day" or pnr.status != "WL" or status.chart_prepared:
        return None
    return Alert(
        alert_id="D1",
        severity=SEVERITY_INFO,
        message="Your waitlist position has moved up since booking.",
        action=None,
        requires_reasoning=False,
        dedup_key="boarding_day",
        payload={"pnr": pnr.pnr},
    )


def _d2_d3_chart_prepared(pnr: PNRRecord, status: JourneyStatus) -> Alert | None:
    if not status.chart_prepared or status.is_cancelled or pnr.status != "WL":
        return None
    if status.cleared:
        coach, berth_a, berth_b = _synthetic_seat(pnr.pnr)
        return Alert(
            alert_id="D2",
            severity=SEVERITY_INFO,
            message=(
                f"Confirmed. {coach}, berths {berth_a} and {berth_b}."
                if len(pnr.passengers) > 1
                else f"Confirmed. {coach}, berth {berth_a}."
            ),
            action="View ticket",
            requires_reasoning=False,
            dedup_key="chart_prepared",
            payload={"pnr": pnr.pnr, "cleared": True, "coach": coach},
        )
    return Alert(
        alert_id="D3",
        severity=SEVERITY_CRITICAL,
        message=(
            f"Didn't clear. Auto-cancelled, ₹{pnr.total_fare:,} refunding "
            "-- you don't need to file anything."
        ),
        action="Find alternatives",
        requires_reasoning=False,
        dedup_key="chart_prepared",
        payload={"pnr": pnr.pnr, "cleared": False, "refund_amount": pnr.total_fare},
    )


def _d4_platform_assigned(pnr: PNRRecord, status: JourneyStatus) -> Alert | None:
    if status.demo_state not in ("boarding_day", "delay_1h", "delay_3h") or status.is_cancelled:
        return None
    if status.effective_status == "WL":
        return None  # no platform for a ticket that hasn't cleared
    platform = _synthetic_platform(pnr.train_number)
    return Alert(
        alert_id="D4",
        severity=SEVERITY_INFO,
        message=f"Platform {platform}.",
        action=None,
        requires_reasoning=False,
        dedup_key="boarding_day",
        payload={"pnr": pnr.pnr, "platform": platform},
    )


def _d6_delay_crosses_1h(pnr: PNRRecord, status: JourneyStatus) -> Alert | None:
    if status.is_cancelled:
        return None
    if not (DELAY_1H_THRESHOLD_MINUTES <= status.delay_minutes < TDR_DELAY_THRESHOLD_MINUTES):
        return None
    hours, minutes = divmod(status.delay_minutes, 60)
    return Alert(
        alert_id="D6",
        severity=SEVERITY_INFO,
        message=f"Running {hours}h {minutes}m late.",
        action=None,
        requires_reasoning=False,
        dedup_key=f"delay_{status.delay_minutes}",
        payload={"pnr": pnr.pnr, "delay_minutes": status.delay_minutes},
    )


def _d8_delay_crosses_3h(pnr: PNRRecord, status: JourneyStatus) -> Alert | None:
    # Detection only in Phase 3. The model composes the actual recommendation
    # from real TDR figures once Phase 4's domain/tdr.py exists -- see
    # docs/04-implementation-plan.md's own Day 3 (detect) / Day 4 (wire) split.
    if not status.tdr_eligible or status.is_cancelled:
        return None
    hours, minutes = divmod(status.delay_minutes, 60)
    return Alert(
        alert_id="D8",
        severity=SEVERITY_CRITICAL,
        message=f"{pnr.train_number} is running {hours}h {minutes}m late.",
        action="File / decide",
        requires_reasoning=True,
        dedup_key="delay_3h",
        payload={
            "pnr": pnr.pnr,
            "delay_minutes": status.delay_minutes,
            "tdr_deadline_iso": status.tdr_deadline_iso,
            "total_fare": pnr.total_fare,
        },
    )


def _d9_retiring_room_bookable(pnr: PNRRecord, status: JourneyStatus) -> Alert | None:
    if not status.retiring_room_eligible or pnr.status != "WL":
        return None  # only interesting as a change-of-state for a ticket that WAS waitlisted
    return Alert(
        alert_id="D9",
        severity=SEVERITY_INFO,
        message=f"You're confirmed now, so a retiring room is available at {pnr.to_station}.",
        action="Check rooms",
        requires_reasoning=False,
        dedup_key="chart_prepared",
        payload={"pnr": pnr.pnr, "station": pnr.to_station},
    )
