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
    journey_id: Mapped[str] = mapped_column(ForeignKey("journeys.id"))
    pnr_number: Mapped[str]
    train_number: Mapped[str]
    travel_class: Mapped[str]
    status: Mapped[str]
    fare_total: Mapped[int]
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
    pnr_id: Mapped[str] = mapped_column(ForeignKey("pnrs.id"))
    reason_code: Mapped[str]
    status: Mapped[str] = mapped_column(default="filed")
    filed_at: Mapped[datetime] = mapped_column(default=_utcnow)
    expected_refund_date: Mapped[datetime | None]
    refund_amount: Mapped[int | None]


class FiredAlert(Base):
    __tablename__ = "fired_alerts"

    id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(index=True)
    journey_id: Mapped[str | None] = mapped_column(ForeignKey("journeys.id"))
    alert_id: Mapped[str]
    severity: Mapped[str]
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
