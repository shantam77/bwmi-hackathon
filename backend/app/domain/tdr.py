"""TDR (Ticket Deposit Receipt) eligibility, deadline computation, and
reason-code selection. Pure Python -- no FastAPI, no OpenAI, no ORM imports.

Deadline rules sourced from docs/01-research-context-log.md section 5.
Sources disagree on some exact windows (one cites a ~4h general rule,
another 30 minutes before departure for the delay case) -- this implements
ONE consistent set, disclosed here and in the product's honesty panel, not
claimed as authoritative. All boundary comparisons are second-precise
(timedelta/datetime), not rounded to whole minutes, so "2h59m59s" and
"3h00m01s" land on the correct side of a threshold."""

from datetime import datetime, timedelta

from app.dataset import TDR_REASON_CODES
from app.models import TDREligibility

REASON_CODES_BY_CODE = {r.code: r for r in TDR_REASON_CODES}

DELAY_THRESHOLD = timedelta(hours=3)
DOWNGRADE_WINDOW = timedelta(hours=3)
GENERAL_WINDOW = timedelta(hours=72)


def _from_reason(
    code: str, eligible: bool, auto_refund: bool, deadline: datetime | None
) -> TDREligibility:
    reason = REASON_CODES_BY_CODE[code]
    return TDREligibility(
        eligible=eligible,
        auto_refund=auto_refund,
        reason_code=reason.code,
        reason_label=reason.label,
        deadline_iso=deadline.isoformat() if deadline else None,
        refund_basis=reason.refund_basis,
        needs_certificate=reason.needs_certificate,
    )


def check_delay_eligibility(delay: timedelta, scheduled_departure: datetime) -> TDREligibility:
    """Train running late, passenger chooses not to travel. Deadline is
    before the train's ACTUAL (delayed) departure."""
    if delay < DELAY_THRESHOLD:
        return TDREligibility(
            eligible=False,
            auto_refund=False,
            reason_code=None,
            reason_label=None,
            deadline_iso=None,
            refund_basis=None,
            needs_certificate=False,
        )
    actual_departure = scheduled_departure + delay
    return _from_reason("LATE_3H", eligible=True, auto_refund=False, deadline=actual_departure)


def check_cancellation_eligibility() -> TDREligibility:
    """Train fully cancelled by Railways -- refunds automatically, no
    filing needed. No time limit, so no deadline to show."""
    return _from_reason("TRAIN_CANCELLED", eligible=False, auto_refund=True, deadline=None)


def check_waitlist_not_cleared_eligibility() -> TDREligibility:
    """Waitlisted ticket never confirmed after chart preparation --
    auto-cancelled, refund automatic. No filing needed."""
    return _from_reason("WAITLIST_NOT_CLEARED", eligible=False, auto_refund=True, deadline=None)


def check_downgrade_eligibility(now: datetime, actual_departure: datetime) -> TDREligibility:
    """Travelled in a lower class than booked. Deadline is within 3 hours
    of actual departure."""
    deadline = actual_departure + DOWNGRADE_WINDOW
    if now > deadline:
        return TDREligibility(
            eligible=False,
            auto_refund=False,
            reason_code=None,
            reason_label=None,
            deadline_iso=None,
            refund_basis=None,
            needs_certificate=False,
        )
    return _from_reason("CLASS_DOWNGRADE", eligible=True, auto_refund=False, deadline=deadline)


def check_general_eligibility(now: datetime, scheduled_arrival: datetime) -> TDREligibility:
    """Other general cases -- within 72 hours of scheduled arrival."""
    deadline = scheduled_arrival + GENERAL_WINDOW
    if now > deadline:
        return TDREligibility(
            eligible=False,
            auto_refund=False,
            reason_code=None,
            reason_label=None,
            deadline_iso=None,
            refund_basis=None,
            needs_certificate=False,
        )
    return _from_reason("GENERAL", eligible=True, auto_refund=False, deadline=deadline)
