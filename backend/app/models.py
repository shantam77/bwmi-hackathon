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
    quota: str
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


class PassengerInput(BaseModel):
    name: str
    age: int
    berth_preference: str | None = None


class BookingQuote(BaseModel):
    train_number: str
    train_name: str
    from_station: str
    to_station: str
    date: str
    travel_class: str
    status: str
    seats_or_position: int
    passengers: list[PassengerInput]
    fare_per_passenger: int
    total_fare: int
    senior_citizen_note: str | None = None


class BookingConfirmation(BaseModel):
    pnr: str
    train_number: str
    train_name: str
    departure: str
    date: str
    travel_class: str
    status: str
    passengers: list[PassengerInput]
    total_fare: int


class PNRRecord(BaseModel):
    pnr: str
    train_number: str
    train_name: str
    from_station: str
    to_station: str
    date: str
    departure: str
    travel_class: str
    status: str
    total_fare: int
    passengers: list[PassengerInput]


class JourneyStatus(BaseModel):
    """Everything the alert engine and the gate table need, computed fresh
    from the PNR + simulated clock every time -- never stored independently.
    Not a rigid named-state enum; PDD section 8's gate table is really a set
    of facts, and facts are what this models."""

    pnr: str
    demo_state: str | None
    now_iso: str
    scheduled_departure_iso: str
    delay_minutes: int
    is_cancelled: bool
    chart_prepared: bool
    cleared: bool | None  # None until chart_prepared; True/False after
    effective_status: str  # "WL" | "RAC" | "CNF"
    tdr_eligible: bool
    tdr_deadline_iso: str | None
    tdr_auto_refund: bool  # cancelled or never-cleared WL -- no filing needed
    retiring_room_eligible: bool
