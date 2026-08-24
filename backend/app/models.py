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
    arrival: str
    # Relative to `date` -- 0 = arrives same day, 1 = arrives the next day.
    # Needed to know which CALENDAR day an overnight train's arrival is on
    # (e.g. 12295 departs 20:00, arrives 06:15 the next day).
    arrival_day_offset: int
    travel_class: str
    status: str
    total_fare: int
    passengers: list[PassengerInput]
    # Set when this booking is one leg of a two-leg connecting journey --
    # points at the OTHER leg's PNR number. IRCTC has no concept of a
    # connected journey; this is our own bookkeeping so the app can reason
    # across two otherwise-unrelated tickets (Flow H).
    linked_pnr: str | None = None


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


class TDREligibility(BaseModel):
    """Result of checking one TDR scenario against docs/01 section 5's
    reason-code table. eligible=False + auto_refund=True means "don't file,
    it refunds automatically" -- half the value of the feature per the PDD."""

    eligible: bool
    auto_refund: bool
    reason_code: str | None
    reason_label: str | None
    deadline_iso: str | None
    refund_basis: str | None
    needs_certificate: bool


class RefundBreakdown(BaseModel):
    fare_total: int
    charge: int
    refund_amount: int
    basis: str  # human-readable description of how the charge was computed


class TDRClaimRecord(BaseModel):
    tdr_id: str
    pnr: str
    reason_code: str
    reason_label: str
    status: str  # "filed" | "accepted"
    filed_at_iso: str
    expected_refund_date_iso: str
    refund_amount: int


class DecisionOption(BaseModel):
    """One named option in Flow H's DecisionBlock -- itemized amounts, its
    own deadline, a bottom-line total. Every figure here traces to a domain
    function; nothing is model-generated."""

    name: str
    items: list[dict]  # [{"label": str, "amount": int, "note": str | None}]
    deadline_iso: str | None
    bottom_line_recovered: int
    bottom_line_total_paid: int


class DecisionBlockData(BaseModel):
    option_1: DecisionOption
    option_2: DecisionOption
    recommendation: str
    leg2_rule_explanation: str
