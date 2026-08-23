from pydantic import BaseModel

# --- Reference data (loaded from backend/data/*.json) -----------------------


class Station(BaseModel):
    code: str
    name: str
    city: str
    tier: str
    aliases: list[str]


class Train(BaseModel):
    number: str
    name: str
    classes: list[str]
    days_of_operation: list[str]


class ScheduleStop(BaseModel):
    train_number: str
    station_code: str
    sequence: int
    arrival: str | None
    departure: str | None
    halt_minutes: int
    day_offset: int


class AvailabilityEntry(BaseModel):
    train_number: str
    travel_class: str
    quota: str
    status: str  # "AVAILABLE" | "WL" | "RAC"
    seats_or_position: int
    fare_per_passenger: int
    date: str


class WaitlistQuota(BaseModel):
    quota: str
    waitlist_type: str
    clearance_ceiling: int
    seasonal_modifier: float
    description: str


class CateringVendor(BaseModel):
    station_code: str
    name: str
    cutoff_minutes: int
    price_band: str
    menu_highlight: str


class RetiringRoomOption(BaseModel):
    station_code: str
    room_type: str
    tariff: int
    min_hours: int
    max_hours: int
    available: bool


class TDRReasonCode(BaseModel):
    code: str
    label: str
    deadline_rule: str
    refund_basis: str
    needs_certificate: bool
    auto_refund: bool


# --- Domain result types (produced by app/domain/*.py) ----------------------


class StationMatch(BaseModel):
    station: Station
    score: float


class StationResolution(BaseModel):
    query: str
    matches: list[StationMatch]
    ambiguous: bool


class Leg(BaseModel):
    train_number: str
    train_name: str
    from_station: str
    to_station: str
    departure: str
    arrival: str
    departure_day_offset: int
    arrival_day_offset: int
    travel_class: str
    status: str
    seats_or_position: int
    fare_per_passenger: int


class JourneyPlan(BaseModel):
    legs: list[Leg]
    direct: bool
    interchange: str | None = None
    layover_minutes: int | None = None


class WaitlistPrediction(BaseModel):
    band: str  # "confirm" | "probable" | "low"
    probability: float
    waitlist_type: str
    position: int
    explanation: str
