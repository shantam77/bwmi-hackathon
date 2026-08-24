"""Halt-aware catering: filter vendors to only what can actually arrive in
time. Pure Python -- no FastAPI, no OpenAI, no ORM imports. The filtering
IS the product (PDD Flow E) -- the list itself is commodity.

Boundary rule: a vendor whose cutoff_minutes exactly equals the time
remaining is INCLUDED (you have exactly enough notice), consistent with how
every other deadline in this app treats "at exactly the threshold" as still
valid (TDR eligibility at exactly 3h, the general TDR window at exactly
72h)."""

from app.dataset import CATERING_VENDORS
from app.models import CateringVendor


def available_vendors(station_code: str, minutes_until_arrival: int) -> tuple[list[CateringVendor], int]:
    """Returns (vendors that can still make the cutoff, count hidden because
    they can't) -- the hidden count is what PDD Flow E shows the user
    ("I've hidden two others that can't")."""
    all_vendors = [v for v in CATERING_VENDORS if v.station_code == station_code]
    available = [v for v in all_vendors if v.cutoff_minutes <= minutes_until_arrival]
    hidden_count = len(all_vendors) - len(available)
    return available, hidden_count
