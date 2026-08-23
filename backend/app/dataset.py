"""Loads reference data from backend/data/*.json once, at import time.
Read-only, version-controlled, hand-editable -- no database involved."""

import json
from pathlib import Path

from app.models import (
    AvailabilityEntry,
    CateringVendor,
    RetiringRoomOption,
    ScheduleStop,
    Station,
    TDRReasonCode,
    Train,
    WaitlistQuota,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load(filename: str) -> dict:
    with open(DATA_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


STATIONS: list[Station] = [Station(**row) for row in _load("stations.json")["stations"]]
TRAINS: list[Train] = [Train(**row) for row in _load("trains.json")["trains"]]
SCHEDULE_STOPS: list[ScheduleStop] = [
    ScheduleStop(**row) for row in _load("schedules.json")["stops"]
]
AVAILABILITY: list[AvailabilityEntry] = [
    AvailabilityEntry(**row) for row in _load("availability.json")["entries"]
]
WAITLIST_QUOTAS: list[WaitlistQuota] = [
    WaitlistQuota(**row) for row in _load("waitlist_model.json")["quotas"]
]
CATERING_VENDORS: list[CateringVendor] = [
    CateringVendor(**row) for row in _load("catering.json")["vendors"]
]
RETIRING_ROOMS: list[RetiringRoomOption] = [
    RetiringRoomOption(**row) for row in _load("retiring_rooms.json")["stations"]
]
TDR_REASON_CODES: list[TDRReasonCode] = [
    TDRReasonCode(**row) for row in _load("tdr_rules.json")["reason_codes"]
]

STATIONS_BY_CODE: dict[str, Station] = {s.code: s for s in STATIONS}
TRAINS_BY_NUMBER: dict[str, Train] = {t.number: t for t in TRAINS}
WAITLIST_QUOTAS_BY_QUOTA: dict[str, WaitlistQuota] = {q.quota: q for q in WAITLIST_QUOTAS}


def schedule_for_train(train_number: str) -> list[ScheduleStop]:
    stops = [s for s in SCHEDULE_STOPS if s.train_number == train_number]
    return sorted(stops, key=lambda s: s.sequence)


def availability_for_train(train_number: str) -> list[AvailabilityEntry]:
    return [a for a in AVAILABILITY if a.train_number == train_number]
