"""Retiring room eligibility and options. Pure Python -- no FastAPI, no
OpenAI, no ORM imports.

Strict gate: a waitlisted PNR never sees a room offer, matching the real
rr.irctc.co.in rule (CNF/RAC only) -- enforcing a real rule the incumbent
enforces is a cheap, high-value credibility signal per the PDD."""

from app.dataset import RETIRING_ROOMS
from app.models import RetiringRoomOption

ELIGIBLE_STATUSES = ("CNF", "RAC")


def room_options(station_code: str, effective_status: str) -> list[RetiringRoomOption]:
    if effective_status not in ELIGIBLE_STATUSES:
        return []
    return [r for r in RETIRING_ROOMS if r.station_code == station_code and r.available]
