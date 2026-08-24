import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Every table below carries session_id, and every store.py query filters on
# it. No cross-session reads, ever -- see docs/04-implementation-plan.md
# section 1 ("Session isolation").


class ClockOffset(Base):
    __tablename__ = "clock_offsets"

    session_id: Mapped[str] = mapped_column(primary_key=True)
    offset_seconds: Mapped[int] = mapped_column(default=0)
    # Which Demo Controls button is currently "active" for this session, so
    # the frontend can show it selected and so engine/state.py can tell a
    # simulated cancellation apart from an ordinary delay. Null = real time.
    demo_state: Mapped[str | None] = mapped_column(default=None)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow, onupdate=_utcnow)


class Journey(Base):
    __tablename__ = "journeys"

    id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(index=True)
    plan_json: Mapped[dict] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(default="DRAFT")
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow, onupdate=_utcnow)


class PNR(Base):
    __tablename__ = "pnrs"

    id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(index=True)
    journey_id: Mapped[str | None] = mapped_column(ForeignKey("journeys.id"))
    pnr_number: Mapped[str]
    train_number: Mapped[str]
    train_name: Mapped[str]
    from_station: Mapped[str]
    to_station: Mapped[str]
    date: Mapped[str]
    departure: Mapped[str]
    arrival: Mapped[str]
    arrival_day_offset: Mapped[int] = mapped_column(default=0)
    travel_class: Mapped[str]
    status: Mapped[str]
    fare_total: Mapped[int]
    # Set when this booking is one leg of a two-leg connecting journey --
    # points at the OTHER leg's pnr_number. Our own bookkeeping; IRCTC has
    # no concept of a connected journey (Flow H).
    linked_pnr: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)


class Passenger(Base):
    __tablename__ = "passengers"

    id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(index=True)
    pnr_id: Mapped[str] = mapped_column(ForeignKey("pnrs.id"))
    name: Mapped[str]
    age: Mapped[int]
    berth_preference: Mapped[str | None]
    concession_flag: Mapped[str | None]


class TDRClaim(Base):
    __tablename__ = "tdr_claims"

    id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(index=True)
    # Plain string, not a FK -- same pattern as FiredAlert.pnr_number.
    pnr_number: Mapped[str]
    reason_code: Mapped[str]
    reason_label: Mapped[str]
    status: Mapped[str] = mapped_column(default="accepted")
    filed_at: Mapped[datetime] = mapped_column(default=_utcnow)
    expected_refund_date: Mapped[datetime]
    refund_amount: Mapped[int]


class FiredAlert(Base):
    __tablename__ = "fired_alerts"

    id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(index=True)
    # Plain string, not a FK -- bookings are tracked by PNR number in this
    # build (see PNR table), there's no populated Journey row to point at.
    pnr_number: Mapped[str]
    alert_id: Mapped[str]
    severity: Mapped[str]
    # Whatever would make this a materially different firing (e.g. the
    # demo_state that triggered it). Jumping to the same demo state twice
    # must not refire the alert; jumping to a worse one should.
    dedup_key: Mapped[str]
    payload_json: Mapped[dict] = mapped_column(JSON)
    fired_at: Mapped[datetime] = mapped_column(default=_utcnow)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(index=True)
    role: Mapped[str]
    content: Mapped[str]
    component_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)


class AgentSessionItem(Base):
    """Raw OpenAI Agents SDK conversation-history items (tool calls, tool
    outputs, reasoning items, etc.) -- deliberately separate from Message,
    which is our own UI-rendering rehydration table. Backs app/agent/session.py's
    PostgresSession, so the SDK's Sessions support lands in this same Postgres
    instance instead of a separate SQLite file."""

    __tablename__ = "agent_session_items"

    id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(index=True)
    sequence: Mapped[int]
    item_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
